from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class Evento(Base):
    __tablename__ = 'eventos'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    data_inicio: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    data_fim: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    classificacao_indicativa: Mapped[str | None] = mapped_column(String(30))
    espaco_id: Mapped[int | None] = mapped_column(Integer)
    responsavel: Mapped[str | None] = mapped_column(String(150))
    publico_estimado: Mapped[int | None] = mapped_column(Integer)
