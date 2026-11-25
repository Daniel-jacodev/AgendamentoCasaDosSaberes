from collections.abc import Generator

from sqlalchemy import URL, CheckConstraint, Table, create_engine, inspect
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.engine import Connection
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.schema import CreateColumn

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


def _atualizar_tabela_eventos(connection: Connection, tabela: Table) -> None:
    inspector = inspect(connection)
    if not inspector.has_table('eventos'):
        return

    columns = {column['name']: column for column in inspector.get_columns('eventos')}
    alteracoes = []
    restricoes = {item['name']: item['sqltext'] for item in inspector.get_check_constraints('eventos')}
    status_anterior = restricoes.get('ck_eventos_status', '')
    if 'cancelado' not in status_anterior or 'negado' not in status_anterior:
        restricao = next(
            item
            for item in tabela.constraints
            if isinstance(item, CheckConstraint) and item.name == 'ck_eventos_status'
        )
        alteracoes.extend([
            'DROP CONSTRAINT IF EXISTS ck_eventos_status',
            f'ADD CONSTRAINT {restricao.name} CHECK ({restricao.sqltext})',
        ])
    for coluna in tabela.columns:
        existente = columns.get(coluna.name)
        if existente is None:
            if coluna.nullable or coluna.server_default is not None:
                tipo = coluna.type.dialect_impl(connection.dialect)
                if isinstance(tipo, ENUM):
                    tipo.create(connection, checkfirst=True)
                definicao = CreateColumn(coluna).compile(dialect=connection.dialect)
                alteracoes.append(f'ADD COLUMN IF NOT EXISTS {definicao}')
        elif coluna.nullable and not existente['nullable']:
            alteracoes.append(f'ALTER COLUMN {coluna.name} DROP NOT NULL')

    for nome, tamanho in (('email', 255), ('entidade', 150)):
        if nome in columns:
            tamanho_atual = columns[nome]['type'].length
            if tamanho_atual is not None and tamanho_atual < tamanho:
                alteracoes.append(f'ALTER COLUMN {nome} TYPE VARCHAR({tamanho})')

    if isinstance(columns.get('classificacao_indicativa', {}).get('type'), ENUM):
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
            # Serializa a migração e a criação de tipos entre inicializações simultâneas.
            connection.exec_driver_sql("SELECT pg_advisory_xact_lock(hashtext('agendamento:init_db'))")
            _atualizar_tabela_eventos(connection, Base.metadata.tables['eventos'])
        Base.metadata.create_all(bind=connection)
