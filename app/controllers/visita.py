from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.schemas.visita import VisitaCreate, VisitaResponse
from app.services import visita as visitaService
from app.services.auth import get_current_user_claims


router = APIRouter(
    prefix="/visitas",
    tags=["Visitas"],
)

T_Session = Annotated[Session, Depends(get_db)]


@router.post(
    "/",
    response_model=VisitaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user_claims)],
)
def create_visita(
    visita: VisitaCreate,
    db: T_Session,
):
    return visitaService.create(
        db,
        visita,
        status_visita="aprovada",
    )


@router.delete(
    "/{visita_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_user_claims)],
)
def delete_visita(
    visita_id: int,
    db: T_Session,
):
    if not visitaService.delete(db, visita_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visita não encontrada.",
        )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )