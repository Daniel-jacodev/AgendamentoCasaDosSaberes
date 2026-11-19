from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.constants.exposicoes import SALAS_EXPOSITIVAS
from app.schemas.conteudo_visita import (
    ExposicaoResponse,
    ExposicaoSalvar,
    ExposicaoStatus,
    ExposicoesAdministracaoResponse,
    ExposicoesResponse,
)
from app.services import conteudo_visita
from app.services.auth import exigir_administrador

router = APIRouter(prefix='/exposicoes', tags=['Exposições'])
T_Session = Annotated[Session, Depends(get_db)]


def validar_sala_expositiva(sala_id: int) -> int:
    if sala_id not in SALAS_EXPOSITIVAS:
        raise HTTPException(404, 'Sala expositiva não encontrada.')
    return sala_id


T_Sala = Annotated[int, Depends(validar_sala_expositiva)]


@router.get('/', response_model=ExposicoesResponse)
def listar_exposicoes(db: T_Session):
    return {'exposicoes': conteudo_visita.listar_exposicoes(db)}


@router.get(
    '/administracao', response_model=ExposicoesAdministracaoResponse, dependencies=[Depends(exigir_administrador)]
)
def listar_exposicoes_administracao(db: T_Session):
    return {
        'salas': [{'id': sala_id, 'nome': nome} for sala_id, nome in SALAS_EXPOSITIVAS.items()],
        'exposicoes': conteudo_visita.listar_exposicoes(db, incluir_pausadas=True),
    }


@router.put('/{sala_id}', response_model=ExposicaoResponse, dependencies=[Depends(exigir_administrador)])
def salvar_exposicao(sala_id: T_Sala, conteudo: ExposicaoSalvar, db: T_Session):
    return conteudo_visita.salvar_exposicao(db, sala_id, conteudo)


@router.put('/{sala_id}/status', response_model=ExposicaoResponse, dependencies=[Depends(exigir_administrador)])
def alterar_status_exposicao(sala_id: T_Sala, status: ExposicaoStatus, db: T_Session):
    exposicao = conteudo_visita.alterar_status_exposicao(db, sala_id, status.pausada)
    if exposicao is None:
        raise HTTPException(404, 'A sala não possui exposição cadastrada.')
    return exposicao
