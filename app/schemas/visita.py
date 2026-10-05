from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class StatusVisita(str, Enum):
    PENDENTE = "pendente"
    APROVADA = "aprovada"
    RECUSADA = "recusada"

class VisitaBase(BaseModel):
    nome_responsavel: str = Field(min_length=3, max_length=120)
    email: EmailStr
    telefone: str = Field(min_length=8, max_length=20)
    instituicao: str | None = Field(default=None, max_length=150)
    quantidade_pessoas: int = Field(gt=0)
    data_inicio: datetime
    data_fim: datetime
    observacoes: str | None = Field(default=None, max_length=1000)

class VisitaCreate(VisitaBase):
    pass

class VisitaResponse(VisitaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: StatusVisita