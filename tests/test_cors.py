import pytest
from fastapi import status


@pytest.mark.parametrize('origin', ['http://127.0.0.1:3000', 'http://localhost:3000'])
@pytest.mark.parametrize('method', ['GET', 'POST', 'PUT', 'DELETE'])
def test_preflight_permite_frontend_local_com_bearer(client, origin, method):
    response = client.options(
        '/eventos/1',
        headers={
            'Origin': origin,
            'Access-Control-Request-Method': method,
            'Access-Control-Request-Headers': 'authorization,content-type',
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.headers['access-control-allow-origin'] == origin
    assert method in response.headers['access-control-allow-methods']
    assert 'authorization' in response.headers['access-control-allow-headers'].lower()


def test_preflight_recusa_origem_desconhecida(client):
    response = client.options(
        '/eventos/1',
        headers={
            'Origin': 'https://outro-site.example',
            'Access-Control-Request-Method': 'DELETE',
            'Access-Control-Request-Headers': 'authorization',
        },
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'access-control-allow-origin' not in response.headers


def test_resposta_401_tem_cors_e_preserva_autenticacao(client):
    response = client.get('/usuarios/me', headers={'Origin': 'http://127.0.0.1:3000'})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers['access-control-allow-origin'] == 'http://127.0.0.1:3000'
