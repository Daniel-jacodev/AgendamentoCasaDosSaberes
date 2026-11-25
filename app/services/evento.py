from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from app.models.arquivo import ArquivoPDF
from app.models.evento import STATUS_EVENTO_ATIVO, Evento
from app.schemas.evento import (
    EventoCreate,
    EventoUpdate,
    EventoWrite,
    StatusEvento,
)
from app.services.disponibilidade import bloquear_agenda, sobreposicao

PASTA_PDFS = Path(__file__).resolve().parents[2] / 'storage' / 'private'
LIMITE_PDF = 30 * 1024 * 1024


def get(
    db: Session,
    *,
    status_evento: StatusEvento | None = None,
    ordenar_por_data: bool = False,
) -> list[Evento]:
    query = select(Evento)

    if status_evento is not None:
        query = query.where(Evento.status == status_evento)

    if ordenar_por_data:
        query = query.order_by(
            Evento.data_inicio,
            Evento.id,
        )

    return list(db.scalars(query))


def _validar_disponibilidade(
    db: Session,
    dados: EventoWrite | Evento,
    evento_id: int | None = None,
) -> None:
    query = select(Evento.id).where(
        Evento.espaco_id == dados.espaco_id,
        Evento.status.in_(STATUS_EVENTO_ATIVO),
        *sobreposicao(
            Evento,
            dados.data_inicio,
            dados.data_fim,
        ),
    )

    if evento_id is not None:
        query = query.where(Evento.id != evento_id)

    evento_conflitante = db.scalar(query.limit(1))

    if evento_conflitante is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=('Já existe um evento nesse espaço e período. Escolha outro horário ou espaço.'),
        )


def create(
    db: Session,
    dados: EventoCreate,
    status_evento: StatusEvento = 'pendente',
    arquivo: UploadFile | None = None,
) -> Evento:
    bloquear_agenda(
        db,
        Evento,
    )

    _validar_disponibilidade(
        db,
        dados,
    )

    valores = dados.model_dump()
    valores['status'] = status_evento
    evento = Evento(**valores)
    caminho = PASTA_PDFS / f'{uuid4()}.pdf' if arquivo is not None else None
    if arquivo is None:
        _validar_arquivo_existente(db, dados.arquivo_pdf_id)
    try:
        if arquivo is not None and caminho is not None:
            evento.arquivo_pdf_id = _salvar_pdf(db, arquivo, caminho)
        db.add(evento)
        db.commit()
    except Exception:
        db.rollback()
        if caminho is not None:
            caminho.unlink(missing_ok=True)
        raise

    db.refresh(evento)

    return evento


def _salvar_pdf(db: Session, arquivo: UploadFile, caminho: Path) -> int:
    conteudo = arquivo.file.read(LIMITE_PDF + 1)
    if arquivo.content_type != 'application/pdf' or not conteudo.startswith(b'%PDF-'):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Apenas arquivos PDF são permitidos.')
    if len(conteudo) > LIMITE_PDF:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'O arquivo excede o limite permitido de 30 MB.')

    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(conteudo)
    registro = ArquivoPDF(
        nome_original=(arquivo.filename or 'documento.pdf')[:255],
        tamanho_bytes=len(conteudo),
        caminho_local=str(caminho),
    )
    db.add(registro)
    db.flush()
    return registro.id


def update(
    db: Session,
    evento_id: int,
    dados: EventoUpdate,
) -> Evento | None:
    bloquear_agenda(
        db,
        Evento,
    )

    evento = db.scalar(select(Evento).where(Evento.id == evento_id))

    if evento is None:
        return None

    if dados.status in STATUS_EVENTO_ATIVO:
        _validar_disponibilidade(db, dados, evento.id)

    valores = dados.model_dump()
    if 'arquivo_pdf_id' not in dados.model_fields_set:
        del valores['arquivo_pdf_id']
    elif dados.arquivo_pdf_id != evento.arquivo_pdf_id:
        _validar_arquivo_existente(db, dados.arquivo_pdf_id)

    if 'aceitou_termos' not in dados.model_fields_set and 'aceitou_termos' in valores:
        del valores['aceitou_termos']

    for key, value in valores.items():
        setattr(
            evento,
            key,
            value,
        )

    db.commit()
    db.refresh(evento)

    return evento


def _validar_arquivo_existente(db: Session, arquivo_pdf_id: int | None) -> None:
    if arquivo_pdf_id is not None and db.get(ArquivoPDF, arquivo_pdf_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, 'Arquivo PDF não encontrado.')


def update_status(
    db: Session,
    evento_id: int,
    novo_status: Literal[
        'aceito',
        'negado',
        'cancelado',
    ],
) -> Evento | None:
    bloquear_agenda(db, Evento)
    evento = db.get(
        Evento,
        evento_id,
    )

    if evento is None:
        return None

    if novo_status in STATUS_EVENTO_ATIVO:
        _validar_disponibilidade(db, evento, evento.id)
    evento.status = novo_status

    db.commit()
    db.refresh(evento)

    return evento


def delete(
    db: Session,
    evento_id: int,
) -> bool:
    evento = db.get(
        Evento,
        evento_id,
    )

    if evento is None:
        return False

    db.delete(evento)
    db.commit()

    return True
