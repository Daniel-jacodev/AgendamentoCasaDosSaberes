from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evento import Evento
from app.schemas.evento import EventoCreate


def get(db: Session):
    eventos = db.scalars(select(Evento)).all()

    return eventos


def create(db: Session, dados: EventoCreate) -> Evento:
    evento = Evento(**dados.model_dump())
    db.add(evento)
    db.commit()
    db.refresh(evento)
    return evento
