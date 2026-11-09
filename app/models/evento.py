import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class SegmentoEnum(str, enum.Enum):
    TEATRO = "Teatro"
    MUSICA = "Música"
    ARTES_VISUAIS = "Artes visuais"
    AUDIOVISUAL = "Audiovisual"
    GESTAO_CULTURAL = "Gestão Cultural"
    DANCA = "Dança"
    OUTRO = "Outro"


class PautaEnum(str, enum.Enum):
    RACIAL = "Racial"
    SOCIAL = "Social"
    INDIGENA = "Indígena"
    PCD = "Pessoas com deficiência"
    COMUNIDADE_LGBTQIAP_PLUS = "Comunidade LGBTQIAP+"
    OUTRO = "Outro"


class PeriodicidadeEnum(str, enum.Enum):
    SEMANAL = "Semanal"
    MENSAL = "Mensal"
    SOMENTE_NA_DATA_ESCOLHIDA = "Somente na data escolhida"


class ClassificacaoIndicativaEnum(str, enum.Enum):
    LIVRE = "Livre"
    DEZ_ANOS = "10 anos"
    DOZE_ANOS = "12 anos"
    CATORZE_ANOS = "14 anos"
    DEZESSEIS_ANOS = "16 anos"
    DEZOITO_ANOS = "18 anos"


class Evento(Base):
    __tablename__ = "eventos"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        default="pendente",
        server_default="pendente",
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
        nullable=True,
    )