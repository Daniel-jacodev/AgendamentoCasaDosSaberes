from datetime import datetime

from sqlalchemy import DateTime, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class ArquivoPDF(Base):
    __tablename__ = 'arquivos_pdf'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome_original: Mapped[str] = mapped_column(String(255), nullable=False)
    tamanho_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), default='application/pdf')
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    dados: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    caminho_local: Mapped[str] = mapped_column(String(500), nullable=False)
