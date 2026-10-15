from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.schemas.evento import EventoCreate, EventoResponse, EventosResponse
from app.services import evento

router = APIRouter(prefix='/eventos', tags=['Eventos'])


@router.get('/', response_model=EventosResponse, status_code=status.HTTP_200_OK)
def get_evento(db: Session = Depends(get_db)):
    return {'eventos': evento.get(db)}


@router.post('/', response_model=EventoResponse, status_code=status.HTTP_201_CREATED)
def create_evento(
    evento: EventoCreate, db: Session = Depends(get_db)
) -> EventoResponse:
    return evento.criar_evento(db, evento)
