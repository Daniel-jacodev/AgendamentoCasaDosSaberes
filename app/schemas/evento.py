from datetime import datetime
from typing import Literal, Self
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EventoBase(BaseModel):
    status: Literal['pendente', 'aceito'] = 'pendente'
    celular: str | None = Field(default=None, max_length=30)
    titulo: str = Field(min_length=3, max_length=150)
    descricao: str = Field(min_length=10, max_length=2000)
    data_inicio: datetime
    data_fim: datetime
    classificacao_indicativa: str | None = None
    espaco_id: Literal[1, 2, 3, 4] = Field(description='1 = Auditorio; 2 = Quintal; 3 = Salas Expositivas; 4 = Varanda')
    responsavel: str | None = None
    publico_estimado: int | None = None


class EventoWrite(EventoBase):
    @field_validator('data_inicio', 'data_fim')
    @classmethod
    def normalizar_horario(cls, valor: datetime) -> datetime:
        # Datas sem offset representam o horario local da Casa de Saberes.
        if valor.tzinfo is not None:
            return valor.astimezone(ZoneInfo('America/Fortaleza')).replace(tzinfo=None)
        return valor

    @model_validator(mode='after')
    def validar_periodo(self) -> Self:
        if self.data_fim <= self.data_inicio:
            raise ValueError('A data de fim deve ser posterior a data de inicio.')
        return self


class EventoCreate(EventoWrite):
    status: Literal['pendente', 'aceito'] = 'pendente'


class EventoUpdate(EventoWrite):
    pass


class EventoResponse(EventoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class EventosResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    eventos: list[EventoResponse]


class EventoFilter(BaseModel):
    titulo: str | None = None  # LIKE
    data_inicio_de: datetime | None = None
    data_inicio_ate: datetime | None = None
    data_fim_de: datetime | None = None
    data_fim_ate: datetime | None = None
    espaco_id: int | None = None
    classificacao_indicativa: str | None = None
    responsavel: str | None = None  # LIKE

    offset: int = Field(default=0, ge=0, description='Quantos registros pular')
    limit: int = Field(default=50, le=200, description='Máximo de registros retornados')

    order_by: Literal['id', 'titulo', 'data_inicio', 'data_fim'] = 'data_inicio'
    order: Literal['asc', 'desc'] = 'asc'
