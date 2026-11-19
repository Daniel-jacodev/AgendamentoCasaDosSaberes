from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.evento import Evento
from app.schemas.evento import EventoCreate, EventoUpdate, EventoWrite


def get(
    db: Session,
    *,
    status_evento: Literal['pendente', 'aceito'] | None = None,
    ordenar_por_data: bool = False,
) -> list[Evento]:
    query = select(Evento)
    if status_evento is not None:
        query = query.where(Evento.status == status_evento)
    if ordenar_por_data:
        query = query.order_by(Evento.data_inicio, Evento.id)
    return list(db.scalars(query))


def _bloquear_agenda(db: Session) -> None:
    # Serializa a verificacao e a gravacao, inclusive quando a agenda esta vazia.
    # O lock e liberado ao encerrar a transacao (commit/rollback).
    if db.get_bind().dialect.name == 'postgresql':
        db.execute(text('LOCK TABLE eventos IN SHARE ROW EXCLUSIVE MODE'))


def _validar_disponibilidade(db: Session, dados: EventoWrite, evento_id: int | None = None) -> None:
    query = select(Evento.id).where(
        Evento.espaco_id == dados.espaco_id,
        Evento.data_inicio < dados.data_fim,
        Evento.data_fim > dados.data_inicio,
    )
    if evento_id is not None:
        query = query.where(Evento.id != evento_id)
    if db.scalar(query.limit(1)) is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            'Ja existe um evento nesse espaco e periodo. Escolha outro horario ou espaco.',
        )


def create(db: Session, dados: EventoCreate, status_evento: str = 'pendente') -> Evento:
    _bloquear_agenda(db)
    _validar_disponibilidade(db, dados)
    valores = dados.model_dump()
    valores['status'] = status_evento
    evento = Evento(**valores)
    db.add(evento)
    db.commit()
    db.refresh(evento)
    return evento


def delete(db: Session, evento_id: int) -> bool:
    evento = db.get(Evento, evento_id)
    if evento is None:
        return False

    db.delete(evento)
    db.commit()
    return True


def update(db: Session, id: int, dados: EventoUpdate) -> Evento | None:
    _bloquear_agenda(db)
    evento = db.scalar(select(Evento).where(Evento.id == id))

    if not evento:
        return None

    _validar_disponibilidade(db, dados, evento.id)

    valores = dados.model_dump()
    if 'aceitou_termos' not in dados.model_fields_set:
        del valores['aceitou_termos']
    for key, value in valores.items():
        setattr(evento, key, value)

    db.commit()
    db.refresh(evento)
    return evento
