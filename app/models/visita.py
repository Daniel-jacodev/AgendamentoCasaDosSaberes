from datetime import datetime
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class StatusVisita(str, Enum):
    PENDENTE = 'pendente'
    APROVADA = 'aprovada'


class Visita(Base):
    __tablename__ = 'visitas'
    __table_args__ = (CheckConstraint("status IN ('pendente', 'aprovada')", name='ck_visitas_status'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(8), default=StatusVisita.PENDENTE.value, server_default='pendente')
    nome_responsavel: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254))
    telefone: Mapped[str] = mapped_column(String(20))
    instituicao: Mapped[str | None] = mapped_column(String(150))
    quantidade_pessoas: Mapped[int] = mapped_column(Integer)
    data_inicio: Mapped[datetime] = mapped_column(DateTime)
    data_fim: Mapped[datetime] = mapped_column(DateTime)
    observacoes: Mapped[str | None] = mapped_column(Text)
