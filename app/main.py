from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.config.database import init_db
from app.controllers.create_evento import router as eventos_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="Agendamento Casa de Saberes", lifespan=lifespan)
app.include_router(eventos_router)
