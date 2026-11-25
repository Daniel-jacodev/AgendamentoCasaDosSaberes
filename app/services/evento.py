from datetime import datetime, time
from heapq import merge
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from app.models.arquivo import ArquivoPDF
from app.models.evento import PERIODICIDADES_RECORRENTES, STATUS_EVENTO_ATIVO, Evento
from app.schemas.evento import (
    EventoCreate,
    EventoPublicoResponse,
    EventoUpdate,
    EventoWrite,
    StatusEvento,
)
from app.services.disponibilidade import bloquear_agenda, validar_horario_evento
from app.services.recorrencia_evento import eventos_no_periodo, intervalos_evento, intervalos_programados

PASTA_PDFS = Path(__file__).resolve().parents[2] / 'storage' / 'private'
LIMITE_PDF = 3 * 1024 * 1024


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


def listar_programacao(db: Session) -> list[EventoPublicoResponse]:
    programacao = []
    for evento in get(db, status_evento='aceito'):
        principal = EventoPublicoResponse.model_validate(evento)
        programacao.extend(
            principal.model_copy(update={'data_inicio': inicio, 'data_fim': fim})
            for inicio, fim in intervalos_programados(evento)
        )
    return sorted(programacao, key=lambda item: (item.data_inicio, item.id))


def _validar_disponibilidade(
    db: Session,
    dados: EventoWrite | Evento,
    status_evento: StatusEvento,
    evento_id: int | None = None,
) -> None:
    limite = dados.data_fim_recorrencia if status_evento == 'aceito' else None
    ultimo_dia = limite or dados.data_fim.date()
    primeiro_dia = dados.data_inicio.date()
    query = select(Evento).where(
        Evento.espaco_id == dados.espaco_id,
        Evento.status.in_(STATUS_EVENTO_ATIVO),
        *eventos_no_periodo(dados.data_inicio, datetime.combine(ultimo_dia, time.max)),
    )
    if evento_id is not None:
        query = query.where(Evento.id != evento_id)

    novos = intervalos_evento((dados.data_inicio, dados.data_fim), dados.periodicidade, limite)
    novo = next(novos, None)
    ocupados = merge(
        *(intervalos_programados(evento, desde=primeiro_dia, ate=ultimo_dia) for evento in db.scalars(query))
    )

    for inicio, fim in ocupados:
        while novo is not None and novo[1] <= inicio:
            novo = next(novos, None)
        if novo is None:
            return
        if novo[0] < fim:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f'Já existe um evento nesse espaço e período ({max(inicio, novo[0]):%d/%m/%Y às %H:%M}). '
                'Escolha outro horário ou espaço.',
            )


def _classificacoes(dados: EventoWrite, evento: Evento | None = None) -> dict:
    valores = {}
    for singular, plural in (('segmento', 'segmentos'), ('pauta', 'pautas')):
        itens = getattr(dados, plural)
        primeiro = getattr(dados, singular)
        if itens is None and evento is not None:
            if singular not in dados.model_fields_set or primeiro == getattr(evento, singular):
                continue
        itens = list(dict.fromkeys(itens if itens is not None else ([primeiro] if primeiro is not None else [])))
        valores[plural] = itens
        valores[singular] = itens[0] if itens else None
    return valores


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
        status_evento,
    )

    validar_horario_evento(dados.data_inicio, dados.data_fim, dados.espaco_id)
    valores = dados.model_dump(exclude={'segmento', 'segmentos', 'pauta', 'pautas'})
    valores.update(
        _classificacoes(dados),
        status=status_evento,
        origem='solicitacao_publica' if status_evento == 'pendente' else 'administrativo',
    )
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
    if arquivo.size is not None and arquivo.size > LIMITE_PDF:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'O arquivo excede o limite permitido de 3 MB.')
    conteudo = arquivo.file.read(LIMITE_PDF + 1)
    if arquivo.content_type != 'application/pdf' or not conteudo.startswith(b'%PDF-'):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Apenas arquivos PDF são permitidos.')
    if len(conteudo) > LIMITE_PDF:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'O arquivo excede o limite permitido de 3 MB.')

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


def consultar_pdf(db: Session, evento_id: int) -> tuple[str, Path | bytes] | None:
    arquivo = db.scalar(
        select(ArquivoPDF).join(Evento, Evento.arquivo_pdf_id == ArquivoPDF.id).where(Evento.id == evento_id)
    )
    if arquivo is None:
        return None
    nome = Path(arquivo.nome_original.replace('\\', '/')).name or 'proposta.pdf'
    raiz = PASTA_PDFS.resolve()
    caminho = Path(arquivo.caminho_local).resolve()
    if caminho.is_relative_to(raiz) and caminho.is_file():
        return nome, caminho
    if arquivo.dados and arquivo.dados.startswith(b'%PDF-'):
        return nome, arquivo.dados
    return None


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

    _atualizar_recorrencia(dados, evento)
    if dados.status in STATUS_EVENTO_ATIVO:
        _validar_disponibilidade(db, dados, dados.status, evento.id)

    if (dados.data_inicio, dados.data_fim, dados.espaco_id) != (evento.data_inicio, evento.data_fim, evento.espaco_id):
        validar_horario_evento(dados.data_inicio, dados.data_fim, dados.espaco_id)

    valores = dados.model_dump(exclude={'segmento', 'segmentos', 'pauta', 'pautas'})
    valores.update(_classificacoes(dados, evento))
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


def _atualizar_recorrencia(dados: EventoUpdate, evento: Evento) -> None:
    if 'periodicidade' not in dados.model_fields_set:
        dados.periodicidade = evento.periodicidade
    mesma_periodicidade = dados.periodicidade == evento.periodicidade
    if mesma_periodicidade and 'data_fim_recorrencia' not in dados.model_fields_set:
        dados.data_fim_recorrencia = evento.data_fim_recorrencia
    limite = dados.data_fim_recorrencia
    if limite is not None and limite < dados.data_inicio.date():
        raise HTTPException(422, 'A data de fim da recorrência deve ser igual ou posterior à data de início.')
    if limite is not None and dados.data_inicio.date() != dados.data_fim.date():
        raise HTTPException(422, 'O início e o fim de cada ocorrência devem ficar no mesmo dia.')
    if dados.periodicidade in PERIODICIDADES_RECORRENTES and limite is None:
        if not mesma_periodicidade or evento.data_fim_recorrencia is not None:
            raise HTTPException(422, 'Informe a data de fim da recorrência semanal ou mensal.')


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
        _validar_disponibilidade(db, evento, novo_status, evento.id)
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
