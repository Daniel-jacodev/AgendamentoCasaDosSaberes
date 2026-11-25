from datetime import date, datetime
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from app.constants.espacos import DESCRICAO_ESPACOS, ESPACO_ID_MAXIMO, ESPACO_ID_MINIMO
from app.models.evento import (
    PERIODICIDADES_RECORRENTES,
    ClassificacaoIndicativaEnum,
    PautaEnum,
    PeriodicidadeEnum,
    SegmentoEnum,
)
from app.services.horario_service import horario_local

StatusEvento = Literal[
    'pendente',
    'aceito',
    'negado',
    'cancelado',
]


class EventoBase(BaseModel):
    titulo: str
    descricao: str
    data_inicio: datetime
    data_fim: datetime

    espaco_id: int = Field(
        description=DESCRICAO_ESPACOS,
    )

    responsavel: str | None = None
    celular: str | None = None
    email: str | None = None
    entidade: str | None = None

    segmento: SegmentoEnum | None = None
    pauta: PautaEnum | None = None
    segmentos: list[SegmentoEnum] | None = Field(default=None, max_length=len(SegmentoEnum))
    pautas: list[PautaEnum] | None = Field(default=None, max_length=len(PautaEnum))
    periodicidade: PeriodicidadeEnum | None = None
    data_fim_recorrencia: date | None = Field(
        default=None, description='Último dia permitido para a recorrência semanal ou mensal, inclusive.'
    )
    classificacao_indicativa: ClassificacaoIndicativaEnum | None = None

    publico_estimado: int | None = None
    link_complementar: str | None = None
    arquivo_pdf_id: int | None = None
    aceitou_termos: bool = False


class EventoWrite(EventoBase):
    titulo: str = Field(
        min_length=3,
        max_length=150,
    )

    descricao: str = Field(
        min_length=10,
        max_length=2000,
    )

    espaco_id: int = Field(
        ge=ESPACO_ID_MINIMO,
        le=ESPACO_ID_MAXIMO,
        description=DESCRICAO_ESPACOS,
    )

    responsavel: str | None = Field(
        default=None,
        min_length=3,
        max_length=150,
    )

    celular: str | None = Field(
        default=None,
        min_length=5,
        max_length=30,
    )

    email: EmailStr | None = None

    entidade: str | None = Field(
        default=None,
        min_length=3,
        max_length=150,
    )

    publico_estimado: int | None = Field(
        default=None,
        gt=0,
    )

    link_complementar: str | None = Field(
        default=None,
        max_length=500,
    )

    arquivo_pdf_id: int | None = Field(
        default=None,
        gt=0,
    )

    @field_validator('data_inicio', 'data_fim')
    @classmethod
    def normalizar_horario(
        cls,
        valor: datetime,
    ) -> datetime:
        return horario_local(valor)

    @model_validator(mode='after')
    def validar_periodo(self) -> Self:
        if self.data_fim <= self.data_inicio:
            raise ValueError('A data de fim deve ser posterior à data de início.')

        if self.periodicidade in PERIODICIDADES_RECORRENTES:
            if self.data_fim_recorrencia is not None and self.data_fim_recorrencia < self.data_inicio.date():
                raise ValueError('A data de fim da recorrência deve ser igual ou posterior à data de início.')
        elif self.data_fim_recorrencia is not None:
            raise ValueError('A data de fim da recorrência se aplica a eventos semanais ou mensais.')

        return self


class EventoCreate(EventoWrite):
    status: StatusEvento = Field(
        default='pendente',
        exclude=True,
    )

    @model_validator(mode='after')
    def validar_fim_recorrencia(self) -> Self:
        recorrente = self.periodicidade in PERIODICIDADES_RECORRENTES
        if recorrente and self.data_fim_recorrencia is None:
            raise ValueError('Informe a data de fim da recorrência semanal ou mensal.')
        return self


class EventoUpdate(EventoWrite):
    status: StatusEvento = 'pendente'


class EventoStatusUpdate(BaseModel):
    status: Literal[
        'aceito',
        'negado',
        'cancelado',
    ]


class EventoResponse(EventoBase):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    status: StatusEvento = 'pendente'
    origem: Literal['solicitacao_publica', 'administrativo'] | None = None

    @model_validator(mode='after')
    def preencher_legado(self) -> Self:
        if self.segmentos is None:
            self.segmentos = [self.segmento] if self.segmento else []
        if self.pautas is None:
            self.pautas = [self.pauta] if self.pauta else []
        if self.origem is None and self.aceitou_termos:
            self.origem = 'solicitacao_publica'
        return self


class EventosResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    eventos: list[EventoResponse]


class EventoPublicoResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    status: Literal['aceito']
    titulo: str
    descricao: str
    classificacao_indicativa: ClassificacaoIndicativaEnum | None
    data_inicio: datetime
    data_fim: datetime
    espaco_id: int

    @computed_field
    @property
    def ocorrencia_id(self) -> str:
        return f'{self.id}:{self.data_inicio.date().isoformat()}'


class EventosPublicosResponse(BaseModel):
    eventos: list[EventoPublicoResponse]


class EventoFilter(BaseModel):
    titulo: str | None = None

    data_inicio_de: datetime | None = None
    data_inicio_ate: datetime | None = None

    data_fim_de: datetime | None = None
    data_fim_ate: datetime | None = None

    espaco_id: int | None = Field(
        default=None,
        ge=ESPACO_ID_MINIMO,
        le=ESPACO_ID_MAXIMO,
    )

    classificacao_indicativa: ClassificacaoIndicativaEnum | None = None

    responsavel: str | None = None

    entidade: str | None = None

    segmento: SegmentoEnum | None = None

    pauta: PautaEnum | None = None

    offset: int = Field(
        default=0,
        ge=0,
        description='Quantos registros pular',
    )

    limit: int = Field(
        default=50,
        ge=1,
        le=200,
        description='Máximo de registros retornados',
    )

    order_by: Literal[
        'id',
        'titulo',
        'data_inicio',
        'data_fim',
    ] = 'data_inicio'

    order: Literal[
        'asc',
        'desc',
    ] = 'asc'
