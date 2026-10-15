from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EventoBase(BaseModel):
    titulo: str = Field(min_length=3, max_length=150)
    descricao: str = Field(min_length=10, max_length=2000)
    data_inicio: datetime
    data_fim: datetime
    classificacao_indicativa: str | None = None
    espaco_id: int | None = None
    responsavel: str | None = None
    publico_estimado: int | None = None


class EventoCreate(EventoBase):
    pass


class EventoResponse(EventoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class EventosResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    eventos: list[EventoResponse]


class EventoFilter(BaseModel):
    titulo: str | None = None # LIKE
    data_inicio_de: datetime | None = None
    data_inicio_ate: datetime | None = None
    data_fim_de: datetime | None = None
    data_fim_ate: datetime | None = None
    espaco_id: int | None = None
    classificacao_indicativa: str | None = None
    responsavel: str | None = None # LIKE

    offset: int = Field(default=0, ge=0, description='Quantos registros pular')
    limit: int = Field(default=50, le=200, description='Máximo de registros retornados')

    order_by: Literal['id', 'titulo', 'data_inicio', 'data_fim'] = 'data_inicio'
    order: Literal['asc', 'desc'] = 'asc'
