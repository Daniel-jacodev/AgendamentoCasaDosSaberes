from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class Visita(Base):
    __tablename__ = "visitas"

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

    nome_responsavel: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    telefone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    instituicao: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    quantidade_pessoas: Mapped[int] = mapped_column(
        Integer,
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

    observacoes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )