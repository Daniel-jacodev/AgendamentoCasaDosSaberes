from datetime import datetime
from enum import Enum
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
)


class StatusVisita(str, Enum):
    PENDENTE = "pendente"
    APROVADA = "aprovada"


class VisitaBase(BaseModel):
    nome_responsavel: str = Field(
        min_length=3,
        max_length=120,
    )

    email: EmailStr

    telefone: str = Field(
        min_length=8,
        max_length=20,
    )

    instituicao: str | None = Field(
        default=None,
        max_length=150,
    )

    quantidade_pessoas: int = Field(
        gt=0,
    )

    data_inicio: datetime
    data_fim: datetime

    observacoes: str | None = Field(
        default=None,
        max_length=1000,
    )


class VisitaCreate(VisitaBase):
    @model_validator(mode="after")
    def validar_periodo(self) -> Self:
        if self.data_fim <= self.data_inicio:
            raise ValueError(
                "A data de fim deve ser posterior à data de início."
            )

        return self


class VisitaResponse(VisitaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: StatusVisita