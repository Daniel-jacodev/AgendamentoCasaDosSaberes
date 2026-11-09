from datetime import datetime
from typing import Literal, Self
from zoneinfo import ZoneInfo

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.constants.espacos import Espaco
from app.models.evento import (
    ClassificacaoIndicativaEnum,
    PautaEnum,
    PeriodicidadeEnum,
    SegmentoEnum,
)


class EventoBase(BaseModel):
    responsavel: str = Field(
        ...,
        min_length=3,
        max_length=150,
    )

    celular: str = Field(
        ...,
        min_length=8,
        max_length=30,
    )

    email: EmailStr

    entidade: str = Field(
        ...,
        min_length=3,
        max_length=150,
    )

    segmento: SegmentoEnum
    pauta: PautaEnum
    periodicidade: PeriodicidadeEnum
    classificacao_indicativa: ClassificacaoIndicativaEnum

    publico_estimado: int = Field(
        ...,
        gt=0,
    )

    titulo: str = Field(
        ...,
        min_length=3,
        max_length=150,
    )

    descricao: str = Field(
        ...,
        min_length=10,
        max_length=2000,
    )

    data_inicio: datetime
    data_fim: datetime

    espaco: Espaco

    link_complementar: str | None = Field(
        default=None,
        max_length=500,
    )

    arquivo_pdf_id: int | None = None


class EventoWrite(EventoBase):

    @field_validator("data_inicio", "data_fim")
    @classmethod
    def normalizar_horario(cls, valor: datetime) -> datetime:
        if valor.tzinfo is not None:
            return (
                valor
                .astimezone(ZoneInfo("America/Fortaleza"))
                .replace(tzinfo=None)
            )

        return valor

    @model_validator(mode="after")
    def validar_periodo(self) -> Self:
        if self.data_fim <= self.data_inicio:
            raise ValueError(
                "A data de fim deve ser posterior à data de início."
            )

        return self


class EventoCreate(EventoWrite):
    pass


class EventoUpdate(EventoWrite):
    status: Literal["pendente", "aceito"] = "pendente"


class EventoResponse(EventoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: Literal["pendente", "aceito"] = "pendente"


class EventosResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    eventos: list[EventoResponse]


class EventoFilter(BaseModel):
    titulo: str | None = None

    data_inicio_de: datetime | None = None
    data_inicio_ate: datetime | None = None
    data_fim_de: datetime | None = None
    data_fim_ate: datetime | None = None

    espaco: Espaco | None = None

    classificacao_indicativa: ClassificacaoIndicativaEnum | None = None
    responsavel: str | None = None
    entidade: str | None = None
    segmento: SegmentoEnum | None = None
    pauta: PautaEnum | None = None

    offset: int = Field(
        default=0,
        ge=0,
        description="Quantos registros pular",
    )

    limit: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Máximo de registros retornados",
    )

    order_by: Literal[
        "id",
        "titulo",
        "data_inicio",
        "data_fim",
    ] = "data_inicio"

    order: Literal["asc", "desc"] = "asc"