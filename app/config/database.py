from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_PATH = Path(__file__).resolve().parents[2] / 'storage' / 'agendamento.db'
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f'sqlite:///{DATABASE_PATH}'

engine = create_engine(
    DATABASE_URL,
    connect_args={'check_same_thread': False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


table_registry = Base.registry  # é usado para configurar os testes
metadata = Base.metadata


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # Importa os models para registrar suas tabelas nos metadados do Base.
    from app.models import evento  # noqa: F401

    Base.metadata.create_all(bind=engine)
