from collections.abc import Generator

from sqlalchemy import URL, create_engine, inspect
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.engine import Connection
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


def _atualizar_tabela_eventos(connection: Connection) -> None:
    inspector = inspect(connection)
    if not inspector.has_table('eventos'):
        return

    columns = {column['name']: column for column in inspector.get_columns('eventos')}
    alteracoes = []
    for nome, tipo in (('link_complementar', 'VARCHAR(500)'), ('arquivo_pdf_id', 'INTEGER')):
        if nome not in columns:
            alteracoes.append(f'ADD COLUMN IF NOT EXISTS {nome} {tipo}')

    for nome in (
        'responsavel',
        'celular',
        'email',
        'entidade',
        'segmento',
        'pauta',
        'periodicidade',
        'classificacao_indicativa',
        'publico_estimado',
    ):
        if not columns[nome]['nullable']:
            alteracoes.append(f'ALTER COLUMN {nome} DROP NOT NULL')

    for nome, tamanho in (('email', 255), ('entidade', 150)):
        tamanho_atual = columns[nome]['type'].length
        if tamanho_atual is not None and tamanho_atual < tamanho:
            alteracoes.append(f'ALTER COLUMN {nome} TYPE VARCHAR({tamanho})')

    if isinstance(columns['classificacao_indicativa']['type'], ENUM):
        # O enum antigo do SQLAlchemy gravava os nomes dos membros.
        alteracoes.append("""
            ALTER COLUMN classificacao_indicativa TYPE VARCHAR(30)
            USING CASE classificacao_indicativa::text
                WHEN 'LIVRE' THEN 'Livre'
                WHEN 'DEZ_ANOS' THEN '10 anos'
                WHEN 'DOZE_ANOS' THEN '12 anos'
                WHEN 'CATORZE_ANOS' THEN '14 anos'
                WHEN 'DEZESSEIS_ANOS' THEN '16 anos'
                WHEN 'DEZOITO_ANOS' THEN '18 anos'
                ELSE classificacao_indicativa::text
            END
        """)

    if alteracoes:
        connection.exec_driver_sql('ALTER TABLE eventos ' + ', '.join(alteracoes))


def init_db() -> None:
    # Importa os models para registrar suas tabelas nos metadados do Base.
    from app import models  # noqa: F401, PLC0415

    with engine.begin() as connection:
        if connection.dialect.name == 'postgresql':
            _atualizar_tabela_eventos(connection)
        Base.metadata.create_all(bind=connection)
