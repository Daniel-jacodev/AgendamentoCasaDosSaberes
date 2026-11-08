import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base

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
        CheckConstraint("status IN ('pendente', 'aceito')", name='ck_eventos_status'),
        CheckConstraint('length(celular) <= 30', name='ck_eventos_celular'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String(8), nullable=False, default='pendente', server_default='pendente')
    responsavel: Mapped[str] = mapped_column(String(150), nullable=False)
    celular: Mapped[str] = mapped_column(String(30), nullable=False)
    email: Mapped[str] = mapped_column(String(50), nullable=False)
    entidade: Mapped[str] = mapped_column(String(50), nullable=False)
    segmento: Mapped[SegmentoEnum] = mapped_column(Enum(SegmentoEnum), nullable=False)
    pauta: Mapped[PautaEnum] = mapped_column(Enum(PautaEnum), nullable=False)
    periodicidade: Mapped[PeriodicidadeEnum] = mapped_column(Enum(PeriodicidadeEnum), nullable=False)
    classificacao_indicativa: Mapped[ClassificacaoIndicativaEnum] = mapped_column(Enum(ClassificacaoIndicativaEnum), nullable=False)
    publico_estimado: Mapped[int] = mapped_column(Integer, nullable=False)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    data_inicio: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    data_fim: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    espaco_id: Mapped[int] = mapped_column(Integer, nullable=False)
