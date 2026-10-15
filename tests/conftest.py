from contextlib import contextmanager
from datetime import datetime

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config.database import get_db, table_registry
from app.main import app
from app.models import Evento


@pytest.fixture
def client(session: AsyncSession):
    def get_db_override():
        return session

    with TestClient(app) as client:
        app.dependency_overrides[get_db] = get_db_override
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine(
        'sqlite+aiosqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(table_registry.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(table_registry.metadata.drop_all)

    engine.dispose()


@pytest_asyncio.fixture
async def evento(session: AsyncSession):
    password = 'secret'
    evento = Evento(
        titulo='Oficina de Flauta Doce',
        descricao='Uma oficina prática focada no ensino de respiração, dedilhado e ornamentações básicas.',
        data_inicio=datetime(2026, 10, 25, 14, 0),
        data_fim=datetime(2026, 10, 25, 16, 0),
        classificacao_indicativa='Livre',
        espaco_id=1,
        responsavel='Coordenação Educativa',
        publico_estimado=25
    )

    session.add(evento)
    await session.commit()
    await session.refresh(evento)

    evento.clean_password = password

    return evento


@pytest.fixture
def token(client, evento):
    response = client.post(
        '/auth/token',
        data={'eventoname': evento.email, 'password': evento.clean_password},
    )

    return response.json()['access_token']


@contextmanager
def _mock_db_time(*, model, time=datetime(2025, 5, 8)):
    def fake_time_hook(mapper, connection, target):
        if hasattr(target, 'created_at'):
            target.created_at = time

        if hasattr(target, 'updated_at'):
            target.updated_at = time

    event.listen(Evento, 'before_insert', fake_time_hook)

    yield time

    event.remove(Evento, 'before_insert', fake_time_hook)


@pytest.fixture
def mock_db_time():
    return _mock_db_time
