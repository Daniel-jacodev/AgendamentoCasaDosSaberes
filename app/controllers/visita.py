from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.visita import StatusVisita
from app.schemas.visita import VisitasPublicasResponse, VisitasResponse
from app.services import visita as visita_service
from app.services.auth import get_current_user_claims

router = APIRouter(prefix='/visitas', tags=['Visitas'])

T_Session = Annotated[Session, Depends(get_db)]


@router.get('/', response_model=VisitasResponse, dependencies=[Depends(get_current_user_claims)])
def get_visitas(db: T_Session):
    return {'visitas': visita_service.get(db)}


@router.get('/pendentes', response_model=VisitasResponse, dependencies=[Depends(get_current_user_claims)])
def get_visitas_pendentes(db: T_Session):
    return {'visitas': visita_service.get(db, status_visita=StatusVisita.PENDENTE)}


@router.get('/aceitas', response_model=VisitasPublicasResponse)
def get_visitas_aceitas(db: T_Session):
    return {'visitas': visita_service.get(db, status_visita=StatusVisita.APROVADA)}


@router.get('/ordenadas', response_model=VisitasResponse, dependencies=[Depends(get_current_user_claims)])
def get_visitas_ordenadas(db: T_Session):
    return {'visitas': visita_service.get(db, ordenar_por_data=True)}
