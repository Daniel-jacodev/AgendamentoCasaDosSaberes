from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


class ExposicaoConteudo(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nome: str = Field(min_length=1, max_length=120)
    descricao: str = Field(default='', max_length=500)
    classificacao: str = Field(default='', max_length=40)


class ExposicaoSalvar(ExposicaoConteudo):
    model_config = ConfigDict(extra='forbid')

    pausada: bool = Field(default=False, strict=True)


class ExposicaoStatus(BaseModel):
    model_config = ConfigDict(extra='forbid')

    pausada: bool = Field(strict=True)


class ExposicaoResponse(ExposicaoConteudo):
    model_config = ConfigDict(from_attributes=True)

    sala_id: int
    pausada: bool


class SalaExpositiva(BaseModel):
    id: int
    nome: str


class ExposicoesResponse(BaseModel):
    exposicoes: list[ExposicaoResponse]


class ExposicoesAdministracaoResponse(ExposicoesResponse):
    salas: list[SalaExpositiva]


OpcaoFormulario = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class CampoFormularioVisita(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

    id: str = Field(min_length=1, max_length=100, pattern=r'^[a-zA-Z0-9_-]+$')
    titulo: str = Field(min_length=1, max_length=500)
    dica: str | None = Field(default=None, max_length=500)
    opcoes: list[OpcaoFormulario] | None = Field(default=None, min_length=1, max_length=100)
    opcional: bool = False
    complementar: bool = False
    multipla: bool = False
    outro: bool = False
    email: bool = False


class FormularioVisitaSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')

    campos: list[CampoFormularioVisita] = Field(max_length=100)

    @model_validator(mode='after')
    def validar_ids(self) -> Self:
        if len({campo.id for campo in self.campos}) != len(self.campos):
            raise ValueError('Os identificadores das perguntas devem ser únicos.')
        return self
