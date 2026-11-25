import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base

STATUS_EVENTO_ATIVO = ('pendente', 'aceito')


class SegmentoEnum(str, enum.Enum):
    TEATRO = 'Teatro'
    MUSICA = 'Música'
    ARTES_VISUAIS = 'Artes visuais'
    AUDIOVISUAL = 'Audiovisual'
    GESTAO_CULTURAL = 'Gestão Cultural'
    DANCA = 'Dança'
    OUTRO = 'Outro'


class PautaEnum(str, enum.Enum):
    RACIAL = 'Racial'
    SOCIAL = 'Social'
    INDIGENA = 'Indígena'
    PCD = 'Pessoas com deficiência'
    COMUNIDADE_LGBTQIAP_PLUS = 'Comunidade LGBTQIAP+'
    OUTRO = 'Outro'


class PeriodicidadeEnum(str, enum.Enum):
    SEMANAL = 'Semanal'
    MENSAL = 'Mensal'
    SOMENTE_NA_DATA_ESCOLHIDA = 'Somente na data escolhida'


class ClassificacaoIndicativaEnum(str, enum.Enum):
    LIVRE = 'Livre'
    DEZ_ANOS = '10 anos'
    DOZE_ANOS = '12 anos'
    CATORZE_ANOS = '14 anos'
    DEZESSEIS_ANOS = '16 anos'
    DEZOITO_ANOS = '18 anos'


class Evento(Base):
    __tablename__ = 'eventos'

    __table_args__ = (
        CheckConstraint(
            "status IN ('pendente', 'aceito', 'negado', 'cancelado')",
            name='ck_eventos_status',
        ),
        CheckConstraint(
            'length(celular) <= 30',
            name='ck_eventos_celular',
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default='pendente',
        server_default='pendente',
    )

    titulo: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    descricao: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    data_inicio: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    data_fim: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    espaco_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    responsavel: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    celular: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    entidade: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    segmento: Mapped[SegmentoEnum | None] = mapped_column(
        Enum(SegmentoEnum),
        nullable=True,
    )

    pauta: Mapped[PautaEnum | None] = mapped_column(
        Enum(PautaEnum),
        nullable=True,
    )

    segmentos: Mapped[list[str] | None] = mapped_column(JSON(none_as_null=True))
    pautas: Mapped[list[str] | None] = mapped_column(JSON(none_as_null=True))
    origem: Mapped[str | None] = mapped_column(String(24))

    periodicidade: Mapped[PeriodicidadeEnum | None] = mapped_column(
        Enum(PeriodicidadeEnum),
        nullable=True,
    )

    classificacao_indicativa: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    publico_estimado: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    link_complementar: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    arquivo_pdf_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey('arquivos_pdf.id', name='fk_eventos_arquivo_pdf', ondelete='SET NULL'),
        nullable=True,
    )

    aceitou_termos: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
