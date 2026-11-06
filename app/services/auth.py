from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwcrypto.common import JWException
from keycloak.exceptions import KeycloakError

from app.config.config import settings
from app.services.keycloak import criar_openid_keycloak

bearer_scheme = HTTPBearer(auto_error=False)


def validar_token_keycloak(token: str) -> dict:
    issuer = settings.keycloak_issuer_url or (
        f'{settings.keycloak_server_url.rstrip("/")}/realms/{settings.keycloak_realm}'
    )
    try:
        payload = criar_openid_keycloak().decode_token(
            token,
            validate=True,
            check_claims={'iss': issuer.rstrip('/'), 'exp': None, 'sub': None, 'aud': settings.keycloak_client_id},
        )
    except KeycloakError as exc:
        raise HTTPException(502, 'Nao foi possivel consultar o provedor de identidade.') from exc
    except (JWException, ValueError, TypeError, KeyError) as exc:
        raise HTTPException(401, 'Token invalido ou expirado.', headers={'WWW-Authenticate': 'Bearer'}) from exc
    return payload


def get_current_user_claims(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict:
    if credentials is None:
        raise HTTPException(401, 'Token Bearer nao informado.', headers={'WWW-Authenticate': 'Bearer'})
    return validar_token_keycloak(credentials.credentials)


def get_optional_user_claims(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict | None:
    if credentials is None:
        return None
    return validar_token_keycloak(credentials.credentials)
