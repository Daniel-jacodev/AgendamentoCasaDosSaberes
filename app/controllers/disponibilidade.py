from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.constants.espacos import ESPACO_ID_MAXIMO, ESPACO_ID_MINIMO
from app.schemas.disponibilidade import DisponibilidadeEspacoResponse
from app.services.disponibilidade import consultar_espaco

router = APIRouter(tags=['Disponibilidade'])


@router.get('/disponibilidade', response_model=DisponibilidadeEspacoResponse)
def get_disponibilidade(
    db: Annotated[Session, Depends(get_db)],
    data: date,
    espaco_id: Annotated[int, Query(ge=ESPACO_ID_MINIMO, le=ESPACO_ID_MAXIMO)],
):
    return consultar_espaco(db, data, espaco_id)
