from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.visita import StatusVisita, Visita


def get(
    db: Session,
    *,
    status_visita: StatusVisita | None = None,
    ordenar_por_data: bool = True,
) -> list[Visita]:
    query = select(Visita)
    if status_visita is not None:
        query = query.where(Visita.status == status_visita.value)
    if ordenar_por_data:
        query = query.order_by(Visita.data_inicio, Visita.id)
    return list(db.scalars(query))
