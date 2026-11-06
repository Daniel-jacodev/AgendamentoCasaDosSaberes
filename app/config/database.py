from collections.abc import Generator

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config.config import settings

DATABASE_URL = URL.create(
    'postgresql+psycopg',
    username=settings.db_user,
    password=settings.db_password,
    host=settings.db_host,
    port=settings.db_port,
    database=settings.db_name,
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={'connect_timeout': 10})
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
    from app.models import evento  # noqa: F401, PLC0415

    Base.metadata.create_all(bind=engine)
