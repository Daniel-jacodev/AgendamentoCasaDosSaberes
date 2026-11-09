import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class NaturezaInstituicaoEnum(str, enum.Enum):
    PUBLICA = "publica"
    PRIVADA = "privada"
    OUTRA = "outra"


class StatusVisitaEnum(str, enum.Enum):
    PENDENTE = "pendente"
    APROVADA = "aprovada"


class Visita(Base):
    __tablename__ = "visitas"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    status: Mapped[StatusVisitaEnum] = mapped_column(
        Enum(StatusVisitaEnum),
        nullable=False,
        default=StatusVisitaEnum.PENDENTE,
    )

    nome_responsavel: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    telefone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    formacao: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    disciplina: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    instituicao: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    natureza_instituicao: Mapped[NaturezaInstituicaoEnum | None] = mapped_column(
        Enum(NaturezaInstituicaoEnum),
        nullable=True,
    )

    grau_escolaridade: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    curso_semestre: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    quantidade_pessoas: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    faixa_etaria: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    composicao_grupo: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    possui_pcd: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    tipos_deficiencia: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    quantidade_pcd: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    data_inicio: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    data_fim: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    observacoes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    aceitou_termos: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )