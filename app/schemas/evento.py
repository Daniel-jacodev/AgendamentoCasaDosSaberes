from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class EventoBase(BaseModel):
    titulo: str = Field(min_length=3, max_length=150)
    descricao: str = Field(min_length=10, max_length=2000)
    data_inicio: datetime
    data_fim: datetime
    classificacao_indicativa: str | None = None
    espaco_id: int | None = None

class EventoCreate(EventoBase):
    pass

class EventoResponse(EventoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int