from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.schemas.evento import EventoCreate, EventoResponse, EventosResponse
from app.services import evento as eventoService

router = APIRouter(prefix='/eventos', tags=['Eventos'])

T_Session = Annotated[Session, Depends(get_db)]


@router.get('/', response_model=EventosResponse, status_code=status.HTTP_200_OK)
def get_evento(db: T_Session):
    return {'eventos': eventoService.get(db)}


@router.post('/', response_model=EventoResponse, status_code=status.HTTP_201_CREATED)
def create_evento(evento: EventoCreate, db: T_Session):
    return eventoService.create(db, evento)


@router.put('/{evento_id}', response_model=EventoResponse, status_code=status.HTTP_200_OK)
def update_evento(evento_id: int, evento: EventoCreate, db: T_Session):
    evento = eventoService.update(db, evento_id, evento)

    if evento == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Evento não encontrado.')

    return evento
