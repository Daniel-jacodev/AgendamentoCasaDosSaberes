import json
import time
from unittest.mock import Mock

import pytest
from fastapi import status
from jwcrypto import jwk, jwt
from keycloak.exceptions import KeycloakGetError, KeycloakPostError

from app.services import auth, keycloak


@pytest.fixture
def provider(monkeypatch):
    admin = Mock()
    admin.create_user.return_value = 'user-id'
    admin.get_user.return_value = {'id': 'user-id', 'email': 'maria@example.com', 'firstName': 'Maria'}
    oidc = Mock()
    oidc.token.return_value = {
        'access_token': 'access',
        'refresh_token': 'refresh',
        'expires_in': 300,
        'refresh_expires_in': 1800,
        'token_type': 'Bearer',
    }
    monkeypatch.setattr(keycloak, '_criar_admin_keycloak', lambda: admin)
    monkeypatch.setattr(keycloak, 'criar_openid_keycloak', lambda: oidc)
    monkeypatch.setattr(auth, 'criar_openid_keycloak', lambda: oidc)
    return admin, oidc


def test_cadastro_e_login(client, provider):
    admin, oidc = provider
    response = client.post('/usuarios', json={'nome': 'Maria', 'email': 'maria@example.com', 'senha': 'senha1234'})
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {'id': 'user-id', 'email': 'maria@example.com', 'nome': 'Maria'}
    payload = admin.create_user.call_args.args[0]
    assert payload['credentials'] == [{'type': 'password', 'value': 'senha1234', 'temporary': False}]
    assert 'realmRoles' not in payload
    response = client.post('/usuarios/login', json={'email': 'maria@example.com', 'senha': 'senha1234'})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['access_token'] == 'access'
    assert response.headers['cache-control'] == 'no-store'
    oidc.token.assert_called_once_with('maria@example.com', 'senha1234')


def test_cadastro_duplicado(client, provider):
    provider[0].create_user.side_effect = KeycloakPostError(response_code=status.HTTP_409_CONFLICT)
    response = client.post('/usuarios', json={'nome': 'Maria', 'email': 'maria@example.com', 'senha': 'senha1234'})
    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.parametrize(
    ('code', 'expected'),
    [
        (status.HTTP_401_UNAUTHORIZED, status.HTTP_401_UNAUTHORIZED),
        (status.HTTP_500_INTERNAL_SERVER_ERROR, status.HTTP_502_BAD_GATEWAY),
    ],
)
def test_erro_login(client, provider, code, expected):
    provider[1].token.side_effect = KeycloakPostError(response_code=code)
    response = client.post('/usuarios/login', json={'email': 'maria@example.com', 'senha': 'errada'})
    assert response.status_code == expected


def test_validacao_cadastro(client):
    assert (
        client.post('/usuarios', json={'nome': ' ', 'email': 'invalido', 'senha': 'curta'}).status_code
        == status.HTTP_422_UNPROCESSABLE_CONTENT
    )


def test_perfil_sem_token(client):
    assert client.get('/usuarios/me').status_code == status.HTTP_401_UNAUTHORIZED


def test_perfil_autenticado(client, provider):
    provider[1].decode_token.return_value = {'sub': 'user-id'}
    response = client.get('/usuarios/me', headers={'Authorization': 'Bearer token'})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['id'] == 'user-id'
    options = provider[1].decode_token.call_args.kwargs
    assert options['validate'] is True
    assert options['check_claims']['aud'] == auth.settings.keycloak_client_id


def test_token_invalido(client, provider):
    provider[1].decode_token.side_effect = ValueError('invalid')
    assert (
        client.get('/usuarios/me', headers={'Authorization': 'Bearer invalid'}).status_code
        == status.HTTP_401_UNAUTHORIZED
    )


def test_provedor_indisponivel(client, provider):
    provider[1].decode_token.side_effect = KeycloakGetError(response_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    assert (
        client.get('/usuarios/me', headers={'Authorization': 'Bearer token'}).status_code == status.HTTP_502_BAD_GATEWAY
    )


@pytest.mark.parametrize('invalid_claim', ['iss', 'aud', 'exp', 'signature'])
def test_validacao_criptografica(client, monkeypatch, invalid_claim):
    signing_key = jwk.JWK.generate(kty='RSA', size=2048)
    claims = {
        'sub': 'user-id',
        'iss': auth.settings.keycloak_issuer_url
        or (f'{auth.settings.keycloak_server_url.rstrip("/")}/realms/{auth.settings.keycloak_realm}'),
        'aud': auth.settings.keycloak_client_id,
        'exp': int(time.time()) + 300,
    }
    if invalid_claim == 'exp':
        claims['exp'] = int(time.time()) - 300
    elif invalid_claim in {'iss', 'aud'}:
        claims[invalid_claim] = 'outra-aplicacao'
    token = jwt.JWT(header={'alg': 'RS256'}, claims=claims)
    token.make_signed_token(signing_key)
    public_key = signing_key if invalid_claim != 'signature' else jwk.JWK.generate(kty='RSA', size=2048)
    oidc = keycloak.criar_openid_keycloak()
    monkeypatch.setattr(oidc, 'certs', lambda: {'keys': [json.loads(public_key.export_public())]})
    monkeypatch.setattr(auth, 'criar_openid_keycloak', lambda: oidc)
    response = client.get('/usuarios/me', headers={'Authorization': f'Bearer {token.serialize()}'})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
