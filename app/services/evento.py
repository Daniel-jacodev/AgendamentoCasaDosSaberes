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


def update(db: Session, id: int, dados: EventoCreate):
    evento = db.scalar(select(Evento).where(Evento.id == id))

    if not evento:
        return None

    for key, value in dados.model_dump().items():
        setattr(evento, key, value)

    db.commit()
    db.refresh(evento)
    return evento
