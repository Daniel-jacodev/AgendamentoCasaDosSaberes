from datetime import datetime
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
)

from app.models.visita import (
    NaturezaInstituicaoEnum,
    StatusVisitaEnum,
)


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

    formacao: str | None = Field(
        default=None,
        max_length=150,
    )

    disciplina: str | None = Field(
        default=None,
        max_length=150,
    )

    instituicao: str = Field(
        min_length=2,
        max_length=150,
    )

    natureza_instituicao: NaturezaInstituicaoEnum | None = None

    grau_escolaridade: str | None = Field(
        default=None,
        max_length=100,
    )

    curso_semestre: str | None = Field(
        default=None,
        max_length=150,
    )

    quantidade_pessoas: int = Field(
        gt=0,
    )

    faixa_etaria: str | None = Field(
        default=None,
        max_length=100,
    )

    composicao_grupo: str | None = Field(
        default=None,
        max_length=1000,
    )

    possui_pcd: bool = False

    tipos_deficiencia: str | None = Field(
        default=None,
        max_length=1000,
    )

    quantidade_pcd: int | None = Field(
        default=None,
        ge=0,
    )

    data_inicio: datetime
    data_fim: datetime

    observacoes: str | None = Field(
        default=None,
        max_length=1000,
    )

    aceitou_termos: bool = False


class VisitaCreate(VisitaBase):

    @model_validator(mode="after")
    def validar_periodo(self) -> Self:
        if self.data_fim <= self.data_inicio:
            raise ValueError(
                "A data de fim deve ser posterior à data de início."
            )

        return self

    @model_validator(mode="after")
    def validar_pcd(self) -> Self:
        if not self.possui_pcd:
            self.tipos_deficiencia = None
            self.quantidade_pcd = None

        elif self.quantidade_pcd is None or self.quantidade_pcd <= 0:
            raise ValueError(
                "Informe a quantidade de pessoas com deficiência."
            )

        return self


class VisitaResponse(VisitaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: StatusVisitaEnum