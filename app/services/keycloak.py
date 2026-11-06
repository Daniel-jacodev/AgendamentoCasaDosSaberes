from fastapi import HTTPException, status
from keycloak import KeycloakAdmin, KeycloakOpenID
from keycloak.exceptions import KeycloakConnectionError, KeycloakError

from app.config.config import settings
from app.schemas.usuarios import LoginRequest, UsuarioCreate


def criar_openid_keycloak() -> KeycloakOpenID:
    return KeycloakOpenID(
        server_url=settings.keycloak_server_url,
        realm_name=settings.keycloak_realm,
        client_id=settings.keycloak_client_id,
        client_secret_key=settings.keycloak_client_secret,
        verify=True,
        timeout=10,
    )


def _criar_admin_keycloak() -> KeycloakAdmin:
    if not settings.keycloak_client_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, 'KEYCLOAK_CLIENT_SECRET nao configurado.')
    return KeycloakAdmin(
        server_url=settings.keycloak_server_url,
        realm_name=settings.keycloak_realm,
        client_id=settings.keycloak_client_id,
        client_secret_key=settings.keycloak_client_secret,
        verify=True,
        timeout=10,
    )


def criar_usuario(usuario: UsuarioCreate) -> dict:
    payload = {
        'username': str(usuario.email),
        'email': str(usuario.email),
        'firstName': usuario.nome.strip(),
        'enabled': True,
        'emailVerified': False,
        'credentials': [{'type': 'password', 'value': usuario.senha.get_secret_value(), 'temporary': False}],
    }
    try:
        usuario_id = _criar_admin_keycloak().create_user(payload, exist_ok=False)
    except KeycloakError as exc:
        if getattr(exc, 'response_code', None) == status.HTTP_409_CONFLICT:
            raise HTTPException(status.HTTP_409_CONFLICT, 'Usuario ja cadastrado com este e-mail.') from exc
        if getattr(exc, 'response_code', None) == status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, 'Cadastro recusado. Verifique os dados e a politica de senha.'
            ) from exc
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, 'Nao foi possivel criar o usuario no provedor de identidade.'
        ) from exc
    return {'id': usuario_id, 'email': usuario.email, 'nome': usuario.nome.strip()}


def obter_usuario_keycloak(usuario_id: str) -> dict:
    try:
        usuario = _criar_admin_keycloak().get_user(usuario_id)
    except KeycloakError as exc:
        if getattr(exc, 'response_code', None) == status.HTTP_404_NOT_FOUND:
            raise HTTPException(status.HTTP_404_NOT_FOUND, 'Usuario nao encontrado.') from exc
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, 'Nao foi possivel consultar o provedor de identidade.'
        ) from exc
    return {'id': usuario['id'], 'email': usuario['email'], 'nome': usuario.get('firstName', '')}


def login_keycloak(login: LoginRequest) -> dict:
    try:
        return criar_openid_keycloak().token(str(login.email), login.senha.get_secret_value())
    except KeycloakError as exc:
        if not isinstance(exc, KeycloakConnectionError) and getattr(exc, 'response_code', None) in {
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
        }:
            # invalid_client indica erro de configuracao, nao credenciais do usuario.
            if 'invalid_client' not in str(getattr(exc, 'response_body', '')):
                raise HTTPException(
                    status.HTTP_401_UNAUTHORIZED, 'Email ou senha invalidos.', headers={'WWW-Authenticate': 'Bearer'}
                ) from exc
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, 'Nao foi possivel autenticar no provedor de identidade.'
        ) from exc
