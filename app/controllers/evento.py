import json

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.schemas.evento import EventoCreate, EventoResponse, EventosPublicosResponse, EventosResponse, EventoUpdate
from app.services import evento as eventoService
from app.services.auth import get_current_user_claims, get_optional_user_claims

router = APIRouter(prefix='/eventos', tags=['Eventos'])

T_Session = Annotated[Session, Depends(get_db)]


@router.get('/', response_model=EventosResponse, dependencies=[Depends(get_current_user_claims)])
def get_evento(db: T_Session):
    return {'eventos': eventoService.get(db)}


@router.get('/pendentes', response_model=EventosResponse, dependencies=[Depends(get_current_user_claims)])
def get_eventos_pendentes(db: T_Session):
    return {'eventos': eventoService.get(db, status_evento='pendente')}


@router.get('/aceitos', response_model=EventosPublicosResponse)
def get_eventos_aceitos(db: T_Session):
    return {'eventos': eventoService.get(db, status_evento='aceito')}


@router.get('/ordenados', response_model=EventosResponse, dependencies=[Depends(get_current_user_claims)])
def get_eventos_ordenados(db: T_Session):
    return {'eventos': eventoService.get(db, ordenar_por_data=True)}


@router.post('/', response_model=EventoResponse, status_code=status.HTTP_201_CREATED)
def create_evento(
    db: T_Session,
    claims: Annotated[dict | None, Depends(get_optional_user_claims)],
    dados: Annotated[str, Form(description='JSON correspondente ao schema EventoCreate')],
    arquivo: Annotated[UploadFile | None, File()] = None,
):
  try:
    payload_dict = json.loads(dados)
    evento = EventoCreate.model_validate(payload_dict)
  except json.JSONDecodeError:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail='O campo "dados" deve ser um JSON válido.',
    )
  except ValidationError as exc:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=exc.errors(),
    )

  status_evento = 'aceito' if claims is not None else 'pendente'
  return eventoService.create(db, evento, status_evento, arquivo=arquivo)


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
