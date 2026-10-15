from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.schemas.evento import EventoCreate, EventoResponse
from app.services.evento import criar_evento


router = APIRouter(prefix="/eventos", tags=["Eventos"])


@router.post("/", response_model=EventoResponse, status_code=status.HTTP_201_CREATED)
def create_evento(evento: EventoCreate, db: Session = Depends(get_db)) -> EventoResponse:
    return criar_evento(db, evento)
