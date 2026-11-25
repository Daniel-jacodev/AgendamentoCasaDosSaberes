from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.schemas.evento import (
    EventoCreate,
    EventoResponse,
    EventosPublicosResponse,
    EventosResponse,
    EventoStatusUpdate,
    EventoUpdate,
)
from app.services import evento as eventoService
from app.services.auth import (
    get_current_user_claims,
    get_optional_user_claims,
)

router = APIRouter(
    prefix='/eventos',
    tags=['Eventos'],
)

T_Session = Annotated[
    Session,
    Depends(get_db),
]


@router.get('/')
def get_evento(
    db: T_Session,
    claims: Annotated[
        dict | None,
        Depends(get_optional_user_claims),
    ],
):
    if claims is not None:
        eventos = eventoService.get(db)

        return EventosResponse(
            eventos=eventos,
        )

    eventos = eventoService.get(
        db,
        status_evento='aceito',
        ordenar_por_data=True,
    )

    return EventosPublicosResponse(
        eventos=eventos,
    )


@router.get(
    '/pendentes',
    response_model=EventosResponse,
    dependencies=[Depends(get_current_user_claims)],
)
def get_eventos_pendentes(
    db: T_Session,
):
    return {
        'eventos': eventoService.get(
            db,
            status_evento='pendente',
            ordenar_por_data=True,
        )
    }


@router.get(
    '/aceitos',
    response_model=EventosPublicosResponse,
)
def get_eventos_aceitos(
    db: T_Session,
):
    return {
        'eventos': eventoService.get(
            db,
            status_evento='aceito',
            ordenar_por_data=True,
        )
    }


@router.get(
    '/ordenados',
    response_model=EventosResponse,
    dependencies=[Depends(get_current_user_claims)],
)
def get_eventos_ordenados(
    db: T_Session,
):
    return {
        'eventos': eventoService.get(
            db,
            ordenar_por_data=True,
        )
    }


@router.post(
    '/',
    response_model=EventoResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_evento(
    evento: EventoCreate,
    db: T_Session,
    claims: Annotated[
        dict | None,
        Depends(get_optional_user_claims),
    ],
):
    if claims is not None:
        status_evento = 'aceito'
    else:
        status_evento = 'pendente'

    return eventoService.create(
        db,
        evento,
        status_evento,
    )


@router.put(
    '/{evento_id}',
    response_model=EventoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user_claims)],
)
def update_evento(
    evento_id: int,
    evento: EventoUpdate,
    db: T_Session,
):
    evento_atualizado = eventoService.update(
        db,
        evento_id,
        evento,
    )

    if evento_atualizado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Evento não encontrado.',
        )

    return evento_atualizado


@router.patch(
    '/{evento_id}/status',
    response_model=EventoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user_claims)],
)
def update_evento_status(
    evento_id: int,
    dados: EventoStatusUpdate,
    db: T_Session,
):
    evento = eventoService.update_status(
        db,
        evento_id,
        dados.status,
    )

    if evento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Evento não encontrado.',
        )

    return evento


@router.delete(
    '/{evento_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_user_claims)],
)
def delete_evento(
    evento_id: int,
    db: T_Session,
):
    removido = eventoService.delete(
        db,
        evento_id,
    )

    if not removido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Evento não encontrado.',
        )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
