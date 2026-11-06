from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.schemas.usuarios import LoginRequest, LoginResponse, UsuarioCreate, UsuarioResponse
from app.services.auth import get_current_user_claims
from app.services.keycloak import criar_usuario, login_keycloak, obter_usuario_keycloak

router = APIRouter(prefix='/usuarios', tags=['Usuarios'])


@router.post('', response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def cadastrar_usuario(usuario: UsuarioCreate):
    return criar_usuario(usuario)


@router.post('/login', response_model=LoginResponse)
def login(dados: LoginRequest, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Pragma'] = 'no-cache'
    return login_keycloak(dados)


@router.get('/me', response_model=UsuarioResponse)
def perfil(claims: Annotated[dict, Depends(get_current_user_claims)]):
    return obter_usuario_keycloak(claims['sub'])
