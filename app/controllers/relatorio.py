from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.schemas.relatorio import FiltroRelatorio
from app.services.auth import exigir_administrador
from app.services.relatorio import consultar_relatorio
from app.services.relatorio_pdf import gerar_pdf

router = APIRouter(prefix='/relatorios', tags=['Relatórios'])


class RespostaPDF(Response):
    media_type = 'application/pdf'


@router.get(
    '/agendamentos',
    response_class=RespostaPDF,
    dependencies=[Depends(exigir_administrador)],
    responses={200: {'content': {'application/pdf': {'schema': {'type': 'string', 'format': 'binary'}}}}},
)
def baixar_relatorio_agendamentos(
    filtro: Annotated[FiltroRelatorio, Query()],
    db: Annotated[Session, Depends(get_db)],
) -> RespostaPDF:
    eventos, visitas = consultar_relatorio(db, filtro)
    sufixo = f'-{filtro.status}' if filtro.status != 'todos' else ''
    arquivo = f'relatorio-{filtro.tipo}-{filtro.data_inicio:%Y-%m-%d}-a-{filtro.data_fim:%Y-%m-%d}{sufixo}.pdf'
    return RespostaPDF(
        gerar_pdf(filtro, eventos, visitas),
        headers={'Content-Disposition': f'attachment; filename="{arquivo}"', 'Cache-Control': 'no-store'},
    )
