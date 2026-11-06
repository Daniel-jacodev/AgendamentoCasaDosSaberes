from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.schemas.evento import EventoCreate, EventoResponse, EventosResponse, EventoUpdate
from app.services import evento as eventoService
from app.services.auth import get_current_user_claims, get_optional_user_claims

router = APIRouter(prefix='/eventos', tags=['Eventos'])

T_Session = Annotated[Session, Depends(get_db)]


@router.get('/', response_model=EventosResponse, status_code=status.HTTP_200_OK)
def get_evento(db: T_Session):
    return {'eventos': eventoService.get(db)}


@router.post('/', response_model=EventoResponse, status_code=status.HTTP_201_CREATED)
def create_evento(
    evento: EventoCreate,
    db: T_Session,
    claims: Annotated[dict | None, Depends(get_optional_user_claims)],
):
    status_evento = 'aceito' if claims is not None else 'pendente'
    return eventoService.create(db, evento, status_evento)


@router.put(
    '/{evento_id}',
    response_model=EventoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user_claims)],
)
def update_evento(evento_id: int, evento: EventoUpdate, db: T_Session):
    evento = eventoService.update(db, evento_id, evento)

    if evento == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Evento não encontrado.')

    return evento


@router.delete('/{evento_id}', status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_user_claims)])
def delete_evento(evento_id: int, db: T_Session):
    if not eventoService.delete(db, evento_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Evento não encontrado.')

    return Response(status_code=status.HTTP_204_NO_CONTENT)
