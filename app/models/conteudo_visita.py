from sqlalchemy import JSON, Boolean, CheckConstraint, String, false
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base
from app.constants.exposicoes import SALAS_EXPOSITIVAS


class Exposicao(Base):
    __tablename__ = 'exposicoes'
    __table_args__ = (
        CheckConstraint(f'sala_id IN ({", ".join(map(str, SALAS_EXPOSITIVAS))})', name='ck_exposicoes_sala'),
    )

    sala_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    nome: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str] = mapped_column(String(500))
    classificacao: Mapped[str] = mapped_column(String(40))
    pausada: Mapped[bool] = mapped_column(Boolean, server_default=false())


class FormularioVisita(Base):
    __tablename__ = 'formulario_visita'
    __table_args__ = (CheckConstraint('id = 1', name='ck_formulario_visita_unico'),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    campos: Mapped[list[dict]] = mapped_column(JSON)
