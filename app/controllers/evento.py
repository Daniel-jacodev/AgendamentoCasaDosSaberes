from typing import Annotated
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from app.config.database import get_db
from app.schemas.evento import (
    EventoCreate,
    EventoResponse,
    EventosPublicosResponse,
    EventosResponse,
    EventoStatusUpdate,
    EventoUpdate,
)
from app.services import evento as eventoService
from app.services.auth import (
    exigir_administrador,
    get_current_user_claims,
    get_optional_user_claims,
)

router = APIRouter(
    prefix='/eventos',
    tags=['Eventos'],
)

T_Session = Annotated[
    Session,
    Depends(get_db),
]


@router.get('/')
def get_evento(
    db: T_Session,
    claims: Annotated[
        dict | None,
        Depends(get_optional_user_claims),
    ],
):
    if claims is not None:
        eventos = eventoService.get(db)

        return EventosResponse(
            eventos=eventos,
        )

    eventos = eventoService.get(
        db,
        status_evento='aceito',
        ordenar_por_data=True,
    )

    return EventosPublicosResponse(
        eventos=eventos,
    )


@router.get(
    '/pendentes',
    response_model=EventosResponse,
    dependencies=[Depends(get_current_user_claims)],
)
def get_eventos_pendentes(
    db: T_Session,
):
    return {
        'eventos': eventoService.get(
            db,
            status_evento='pendente',
            ordenar_por_data=True,
        )
    }


@router.get(
    '/aceitos',
    response_model=EventosPublicosResponse,
)
def get_eventos_aceitos(
    db: T_Session,
):
    return {
        'eventos': eventoService.get(
            db,
            status_evento='aceito',
            ordenar_por_data=True,
        )
    }


@router.get(
    '/ordenados',
    response_model=EventosResponse,
    dependencies=[Depends(get_current_user_claims)],
)
def get_eventos_ordenados(
    db: T_Session,
):
    return {
        'eventos': eventoService.get(
            db,
            ordenar_por_data=True,
        )
    }


@router.post(
    '/',
    response_model=EventoResponse,
    status_code=status.HTTP_201_CREATED,
    openapi_extra={
        'requestBody': {
            'required': True,
            'content': {
                'application/json': {'schema': {'$ref': '#/components/schemas/EventoUpdate'}},
                'multipart/form-data': {
                    'schema': {
                        'type': 'object',
                        'required': ['dados'],
                        'properties': {
                            'dados': {'type': 'string', 'description': 'JSON com os dados do evento.'},
                            'arquivo': {'type': 'string', 'format': 'binary'},
                        },
                    },
                },
            },
        },
    },
)
async def create_evento(
    request: Request,
    db: T_Session,
    claims: Annotated[
        dict | None,
        Depends(get_optional_user_claims),
    ],
):
    status_evento = 'aceito' if claims is not None else 'pendente'
    content_type = request.headers.get('content-type', '').split(';', 1)[0].strip().lower()
    if content_type == 'multipart/form-data':
        async with request.form(max_files=1, max_fields=1) as formulario:
            dados = formulario.get('dados')
            arquivo = formulario.get('arquivo')
            if not isinstance(dados, str) or (arquivo is not None and not isinstance(arquivo, UploadFile)):
                raise HTTPException(422, 'Envie o JSON em "dados" e, opcionalmente, o PDF em "arquivo".')
            evento = _validar_dados_evento(dados)
            return await run_in_threadpool(eventoService.create, db, evento, status_evento, arquivo)

    evento = _validar_dados_evento(await request.body())
    return await run_in_threadpool(eventoService.create, db, evento, status_evento)


def _validar_dados_evento(dados: str | bytes) -> EventoCreate:
    try:
        return EventoCreate.model_validate_json(dados)
    except ValidationError as exc:
        erros = [
            {**erro, 'loc': ('body', *erro['loc'])}
            for erro in exc.errors(include_url=False, include_context=False, include_input=False)
        ]
        raise RequestValidationError(erros) from exc


@router.put(
    '/{evento_id}',
    response_model=EventoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user_claims)],
)
def update_evento(
    evento_id: int,
    evento: EventoUpdate,
    db: T_Session,
):
    evento_atualizado = eventoService.update(
        db,
        evento_id,
        evento,
    )

    if evento_atualizado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Evento não encontrado.',
        )

    return evento_atualizado


@router.patch(
    '/{evento_id}/status',
    response_model=EventoResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user_claims)],
)
def update_evento_status(
    evento_id: int,
    dados: EventoStatusUpdate,
    db: T_Session,
):
    evento = eventoService.update_status(
        db,
        evento_id,
        dados.status,
    )

    if evento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Evento não encontrado.',
        )

    return evento


@router.get(
    '/{evento_id}/proposta',
    response_class=FileResponse,
    dependencies=[Depends(exigir_administrador)],
    responses={200: {'content': {'application/pdf': {'schema': {'type': 'string', 'format': 'binary'}}}}},
)
def baixar_proposta(evento_id: int, db: T_Session) -> Response:
    arquivo = eventoService.consultar_pdf(db, evento_id)
    if arquivo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'PDF da proposta não encontrado.')
    nome, conteudo = arquivo
    cabecalhos = {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}
    if isinstance(conteudo, bytes):
        cabecalhos['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(nome, safe='')}"
        return Response(conteudo, media_type='application/pdf', headers=cabecalhos)
    return FileResponse(conteudo, filename=nome, media_type='application/pdf', headers=cabecalhos)


@router.delete(
    '/{evento_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_user_claims)],
)
def delete_evento(
    evento_id: int,
    db: T_Session,
):
    removido = eventoService.delete(
        db,
        evento_id,
    )

    if not removido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Evento não encontrado.',
        )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
