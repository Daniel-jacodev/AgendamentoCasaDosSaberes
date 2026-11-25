from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.visita import STATUS_VISITA_ATIVA, StatusVisitaEnum, Visita
from app.schemas.visita import VisitaCreate
from app.services.disponibilidade import bloquear_agenda, sobreposicao, validar_horario_visita


def get(
    db: Session,
    *,
    status_visita: StatusVisitaEnum | None = None,
    ordenar_por_data: bool = True,
) -> list[Visita]:
    query = select(Visita)
    if status_visita is not None:
        query = query.where(Visita.status == status_visita.value)
    if ordenar_por_data:
        query = query.order_by(Visita.data_inicio, Visita.id)
    return list(db.scalars(query))


def _validar_conflito(db: Session, inicio: datetime, fim: datetime, visita_id: int | None = None) -> None:
    conflito = select(Visita.id).where(
        Visita.id != visita_id, Visita.status.in_(STATUS_VISITA_ATIVA), *sobreposicao(Visita, inicio, fim)
    )
    if db.scalar(conflito.limit(1)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Horário indisponível para visita. Escolha outro horário.')


def create(
    db: Session,
    dados: VisitaCreate,
    status_visita: StatusVisitaEnum,
) -> Visita:
    bloquear_agenda(db, Visita)
    validar_horario_visita(dados.data_inicio, dados.data_fim)
    _validar_conflito(db, dados.data_inicio, dados.data_fim)

    valores = dados.model_dump()
    valores['status'] = status_visita.value

    visita = Visita(**valores)

    db.add(visita)
    db.commit()
    db.refresh(visita)

    return visita


def atualizar_status(db: Session, visita_id: int, novo_status: StatusVisitaEnum) -> Visita | None:
    bloquear_agenda(db, Visita)
    visita = db.get(Visita, visita_id)
    if visita is None or visita.status == novo_status.value:
        return visita
    permitidos = {
        StatusVisitaEnum.PENDENTE.value: {
            StatusVisitaEnum.APROVADA,
            StatusVisitaEnum.NEGADA,
            StatusVisitaEnum.CANCELADA,
        },
        StatusVisitaEnum.APROVADA.value: {StatusVisitaEnum.CANCELADA},
    }
    if novo_status not in permitidos.get(visita.status, set()):
        raise HTTPException(status.HTTP_409_CONFLICT, 'O status atual da visita não permite esta alteração.')
    if novo_status == StatusVisitaEnum.APROVADA:
        _validar_conflito(db, visita.data_inicio, visita.data_fim, visita.id)
    visita.status = novo_status.value
    db.commit()
    db.refresh(visita)
    return visita
