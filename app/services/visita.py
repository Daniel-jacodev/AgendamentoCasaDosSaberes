from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.visita import StatusVisitaEnum, Visita
from app.schemas.visita import VisitaCreate
from app.services.disponibilidade import bloquear_agenda, sobreposicao


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


def create(
    db: Session,
    dados: VisitaCreate,
) -> Visita:
    bloquear_agenda(db, Visita)
    conflito = select(Visita.id).where(*sobreposicao(Visita, dados.data_inicio, dados.data_fim))
    if db.scalar(conflito.limit(1)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Horário indisponível para visita. Escolha outro horário.')

    valores = dados.model_dump()
    valores['status'] = StatusVisitaEnum.APROVADA.value

    visita = Visita(**valores)

    db.add(visita)
    db.commit()
    db.refresh(visita)

    return visita


def delete(
    db: Session,
    visita_id: int,
) -> bool:
    visita = db.get(Visita, visita_id)

    if visita is None:
        return False

    db.delete(visita)
    db.commit()

    return True
