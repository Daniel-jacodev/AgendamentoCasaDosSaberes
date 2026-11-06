from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class Evento(Base):
    __tablename__ = 'eventos'
    __table_args__ = (
        CheckConstraint("status IN ('pendente', 'aceito')", name='ck_eventos_status'),
        CheckConstraint('length(celular) <= 30', name='ck_eventos_celular'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String(8), nullable=False, default='pendente', server_default='pendente')
    celular: Mapped[str | None] = mapped_column(String(30))
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    data_inicio: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    data_fim: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    classificacao_indicativa: Mapped[str | None] = mapped_column(String(30))
    espaco_id: Mapped[int] = mapped_column(Integer, nullable=False)
    responsavel: Mapped[str | None] = mapped_column(String(150))
    publico_estimado: Mapped[int | None] = mapped_column(Integer)
