from sqlalchemy.orm import Session

from app.models.visita import Visita
from app.schemas.visita import VisitaCreate


def create(
    db: Session,
    dados: VisitaCreate,
    status_visita: str = "aprovada",
) -> Visita:
    valores = dados.model_dump()
    valores["status"] = status_visita

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