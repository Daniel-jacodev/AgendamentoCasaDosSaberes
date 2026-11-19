from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.visita import StatusVisitaEnum
from app.schemas.disponibilidade import DisponibilidadeVisitaResponse
from app.schemas.visita import (
    VisitaCreate,
    VisitaResponse,
    VisitasPublicasResponse,
    VisitasResponse,
)
from app.services import visita as visita_service
from app.services.auth import get_current_user_claims
from app.services.disponibilidade import consultar_visitas

router = APIRouter(prefix='/visitas', tags=['Visitas'])

T_Session = Annotated[Session, Depends(get_db)]


@router.get('/disponibilidade', response_model=DisponibilidadeVisitaResponse)
def get_disponibilidade_visitas(db: T_Session, data: date):
    return consultar_visitas(db, data)


@router.get('/', response_model=VisitasResponse, dependencies=[Depends(get_current_user_claims)])
def get_visitas(db: T_Session):
    return {'visitas': visita_service.get(db)}


@router.get('/pendentes', response_model=VisitasResponse, dependencies=[Depends(get_current_user_claims)])
def get_visitas_pendentes(db: T_Session):
    return {'visitas': visita_service.get(db, status_visita=StatusVisitaEnum.PENDENTE)}


@router.get('/aceitas', response_model=VisitasPublicasResponse)
def get_visitas_aceitas(db: T_Session):
    return {'visitas': visita_service.get(db, status_visita=StatusVisitaEnum.APROVADA)}


@router.get('/ordenadas', response_model=VisitasResponse, dependencies=[Depends(get_current_user_claims)])
def get_visitas_ordenadas(db: T_Session):
    return {'visitas': visita_service.get(db, ordenar_por_data=True)}


@router.post(
    '/',
    response_model=VisitaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user_claims)],
)
def create_visita(
    visita: VisitaCreate,
    db: T_Session,
):
    return visita_service.create(
        db,
        visita,
    )


@router.delete(
    '/{visita_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_user_claims)],
)
def delete_visita(
    visita_id: int,
    db: T_Session,
):
    if not visita_service.delete(db, visita_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Visita não encontrada.',
        )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
