from http import HTTPStatus
from unittest.mock import Mock

import pytest

from app.models.evento import Evento
from app.services import auth


@pytest.fixture
def authenticated_headers(monkeypatch):
    oidc = Mock()
    oidc.decode_token.return_value = {'sub': 'user-id'}
    monkeypatch.setattr(auth, 'criar_openid_keycloak', lambda: oidc)
    return {'Authorization': 'Bearer valid-token'}


def test_delete_evento(client, evento, session, authenticated_headers):
    evento_id = evento.id

    response = client.delete(f'/eventos/{evento_id}', headers=authenticated_headers)

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b''
    session.expire_all()
    assert session.get(Evento, evento_id) is None
    assert client.get('/eventos/').json() == {'eventos': []}
    assert client.delete(f'/eventos/{evento_id}', headers=authenticated_headers).status_code == HTTPStatus.NOT_FOUND


def test_delete_evento_not_found(client, evento, authenticated_headers):
    response = client.delete('/eventos/999', headers=authenticated_headers)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Evento não encontrado.'}
    assert len(client.get('/eventos/').json()['eventos']) == 1


def test_get_evento_empty(client):
    response = client.get('/eventos')

    assert response.json() == {'eventos': []}


def test_get_evento_populated(client, evento):
    response = client.get(
        '/eventos',
    )

    assert response.json() == {
        'eventos': [
            {
                'titulo': 'Oficina de Flauta Doce',
                'descricao': 'Uma oficina prática focada no ensino de respiração, dedilhado e ornamentações básicas.',
                'data_inicio': '2026-10-25T14:00:00',
                'data_fim': '2026-10-25T16:00:00',
                'classificacao_indicativa': 'Livre',
                'espaco_id': 1,
                'responsavel': 'Coordenação Educativa',
                'publico_estimado': 25,
                'id': 1,
                'status': 'pendente',
                'celular': None,
            },
        ]
    }


def test_create_evento(client):
    payload = {
        'titulo': 'Oficina de Flauta Doce',
        'descricao': 'Uma oficina prática focada no ensino de respiração, dedilhado e ornamentações básicas.',
        'data_inicio': '2026-10-25T14:00:00',
        'data_fim': '2026-10-25T16:00:00',
        'classificacao_indicativa': 'Livre',
        'espaco_id': 1,
        'responsavel': 'Coordenação Educativa',
        'publico_estimado': 25,
    }

    response = client.post('/eventos', json=payload)

    assert response.status_code == HTTPStatus.CREATED

    data = response.json()
    assert data['id'] == 1
    assert data['titulo'] == payload['titulo']
    assert data['descricao'] == payload['descricao']
    assert data['data_inicio'] == payload['data_inicio']
    assert data['data_fim'] == payload['data_fim']
    assert data['classificacao_indicativa'] == payload['classificacao_indicativa']
    assert data['espaco_id'] == payload['espaco_id']
    assert data['responsavel'] == payload['responsavel']
    assert data['publico_estimado'] == payload['publico_estimado']


def test_update_evento(client, evento, authenticated_headers):
    payload = {
        'titulo': 'Oficina de Flauta Doce e Clarinete',
        'descricao': 'Uma oficina prática focada no ensino de respiração, dedilhado e ornamentações básicas.',
        'data_inicio': '2026-10-25T14:00:00',
        'data_fim': '2026-10-25T16:00:00',
        'classificacao_indicativa': 'Livre',
        'espaco_id': 1,
        'responsavel': 'Coordenação Educativa',
        'publico_estimado': 25,
    }

    response = client.put('/eventos/1', json=payload, headers=authenticated_headers)

    assert response.status_code == HTTPStatus.OK

    data = response.json()
    assert data['id'] == 1
    assert data['titulo'] == payload['titulo']
    assert data['descricao'] == payload['descricao']
    assert data['data_inicio'] == payload['data_inicio']
    assert data['data_fim'] == payload['data_fim']
    assert data['classificacao_indicativa'] == payload['classificacao_indicativa']
    assert data['espaco_id'] == payload['espaco_id']
    assert data['responsavel'] == payload['responsavel']
    assert data['publico_estimado'] == payload['publico_estimado']


def test_update_evento_not_found(client, evento, authenticated_headers):
    payload = {
        'titulo': 'Oficina de Flauta Doce e Clarinete',
        'descricao': 'Uma oficina prática focada no ensino de respiração, dedilhado e ornamentações básicas.',
        'data_inicio': '2026-10-25T14:00:00',
        'data_fim': '2026-10-25T16:00:00',
        'classificacao_indicativa': 'Livre',
        'espaco_id': 1,
        'responsavel': 'Coordenação Educativa',
        'publico_estimado': 25,
    }

    response = client.put('/eventos/999', json=payload, headers=authenticated_headers)

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize('method', ['put', 'delete'])
@pytest.mark.parametrize('authorization', [None, 'Bearer invalid-token'])
def test_mutacao_evento_exige_login(client, evento, monkeypatch, method, authorization):
    oidc = Mock()
    oidc.decode_token.side_effect = ValueError('Token invalido')
    monkeypatch.setattr(auth, 'criar_openid_keycloak', lambda: oidc)
    titulo_original = evento.titulo
    headers = {'Authorization': authorization} if authorization else {}
    payload = {
        'espaco_id': 1,
        'titulo': 'Alteracao indevida',
        'descricao': evento.descricao,
        'data_inicio': evento.data_inicio.isoformat(),
        'data_fim': evento.data_fim.isoformat(),
    }

    response = client.request(method, f'/eventos/{evento.id}', headers=headers, json=payload)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers['www-authenticate'] == 'Bearer'
    eventos = client.get('/eventos/').json()['eventos']
    assert len(eventos) == 1
    assert eventos[0]['id'] == evento.id
    assert eventos[0]['titulo'] == titulo_original


@pytest.mark.parametrize(
    ('inicio', 'fim'),
    [
        ('2026-10-25T14:00:00', '2026-10-25T16:00:00'),
        ('2026-10-25T13:00:00', '2026-10-25T15:00:00'),
        ('2026-10-25T15:00:00', '2026-10-25T17:00:00'),
        ('2026-10-25T14:30:00', '2026-10-25T15:00:00'),
        ('2026-10-25T13:00:00', '2026-10-25T17:00:00'),
        ('2026-10-24T23:00:00', '2026-10-25T15:00:00'),
        ('2026-10-25T17:00:00Z', '2026-10-25T19:00:00Z'),
    ],
)
def test_create_evento_conflitante(client, evento, inicio, fim):
    payload = {
        'espaco_id': 1,
        'titulo': 'Outro evento',
        'descricao': 'Descricao de outro evento.',
        'data_inicio': inicio,
        'data_fim': fim,
    }
    response = client.post('/eventos/', json=payload)
    assert response.status_code == HTTPStatus.CONFLICT
    assert len(client.get('/eventos/').json()['eventos']) == 1


@pytest.mark.parametrize(
    ('inicio', 'fim'),
    [
        ('2026-10-25T12:00:00', '2026-10-25T14:00:00'),
        ('2026-10-25T16:00:00', '2026-10-25T18:00:00'),
        ('2026-10-26T14:00:00', '2026-10-26T16:00:00'),
    ],
)
def test_create_evento_sem_conflito(client, evento, inicio, fim):
    payload = {
        'espaco_id': 1,
        'titulo': 'Outro evento',
        'descricao': 'Descricao de outro evento.',
        'data_inicio': inicio,
        'data_fim': fim,
    }
    assert client.post('/eventos/', json=payload).status_code == HTTPStatus.CREATED


@pytest.mark.parametrize('fim', ['2026-10-25T14:00:00', '2026-10-25T13:00:00'])
def test_evento_periodo_invalido(client, authenticated_headers, fim):
    payload = {
        'espaco_id': 1,
        'titulo': 'Outro evento',
        'descricao': 'Descricao de outro evento.',
        'data_inicio': '2026-10-25T14:00:00',
        'data_fim': fim,
    }
    response = client.post('/eventos/', json=payload)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert client.put('/eventos/1', json=payload, headers=authenticated_headers).status_code == (
        HTTPStatus.UNPROCESSABLE_ENTITY
    )


def test_update_evento_conflitante(client, evento, authenticated_headers):
    payload = {
        'espaco_id': 1,
        'titulo': 'Outro evento',
        'descricao': 'Descricao de outro evento.',
        'data_inicio': '2026-10-25T17:00:00',
        'data_fim': '2026-10-25T18:00:00',
    }
    response = client.post('/eventos/', json=payload)
    evento_id = response.json()['id']
    payload.update(data_inicio='2026-10-25T15:00:00', data_fim='2026-10-25T17:00:00')
    response = client.put(f'/eventos/{evento_id}', json=payload, headers=authenticated_headers)
    assert response.status_code == HTTPStatus.CONFLICT
    eventos = client.get('/eventos/').json()['eventos']
    atualizado = next(item for item in eventos if item['id'] == evento_id)
    assert atualizado['data_inicio'] == '2026-10-25T17:00:00'


@pytest.mark.parametrize('celular', [None, '(85) 99999-1234', '9' * 30])
def test_cadastro_mvp(client, celular):
    payload = {
        'titulo': 'Evento MVP',
        'descricao': 'Descricao do evento MVP.',
        'data_inicio': '2026-12-01T17:00:00Z',
        'data_fim': '2026-12-01T19:00:00Z',
        'espaco_id': 4,
    }
    if celular is not None:
        payload['celular'] = celular
    response = client.post('/eventos/', json=payload)
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['status'] == 'pendente'
    assert data['celular'] == celular
    assert data['data_inicio'] == '2026-12-01T14:00:00'
    assert client.get('/eventos/').json() == {'eventos': [data]}


def test_aprovacao_persistida(client, evento, session, authenticated_headers):
    data = client.get('/eventos/').json()['eventos'][0]
    data.update(status='aceito', celular='(85) 99999-0000')
    response = client.put(f'/eventos/{evento.id}', json=data, headers=authenticated_headers)
    assert response.status_code == HTTPStatus.OK
    assert response.json()['status'] == 'aceito'
    # Recarrega do banco, sem depender do objeto ja carregado pelo ORM.
    session.expire_all()
    assert session.get(Evento, evento.id).status == 'aceito'
    assert session.get(Evento, evento.id).celular == data['celular']
    assert client.get('/eventos/').json()['eventos'][0]['status'] == 'aceito'
    response = client.delete(f'/eventos/{evento.id}', headers=authenticated_headers)
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b''
    assert client.get('/eventos/').json() == {'eventos': []}


@pytest.mark.parametrize('status', ['recusado', 'confirmando', '', None])
def test_status_invalido(client, evento, authenticated_headers, status):
    data = client.get('/eventos/').json()['eventos'][0]
    data['status'] = status
    assert client.post('/eventos/', json=data).status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert client.put('/eventos/1', json=data, headers=authenticated_headers).status_code == (
        HTTPStatus.UNPROCESSABLE_ENTITY
    )


def test_post_anonimo_nao_pode_aprovar(client):
    payload = {
        'espaco_id': 1,
        'titulo': 'Evento MVP',
        'descricao': 'Descricao do evento MVP.',
        'data_inicio': '2026-12-01T14:00:00',
        'data_fim': '2026-12-01T16:00:00',
        'status': 'aceito',
    }
    response = client.post('/eventos/', json=payload)
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['status'] == 'pendente'


def test_celular_longo(client):
    payload = {
        'espaco_id': 1,
        'titulo': 'Evento MVP',
        'descricao': 'Descricao do evento MVP.',
        'data_inicio': '2026-12-01T14:00:00',
        'data_fim': '2026-12-01T16:00:00',
        'celular': '9' * 31,
    }
    response = client.post('/eventos/', json=payload)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.parametrize('method', ['put', 'delete'])
def test_aprovacao_recusa_sem_login(client, evento, method):
    data = client.get('/eventos/').json()['eventos'][0]
    data['status'] = 'aceito'
    response = client.request(method, f'/eventos/{evento.id}', json=data)
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert client.get('/eventos/').json()['eventos'][0]['status'] == 'pendente'


def test_criacao_administrativa_aceita_imediatamente(client, authenticated_headers):
    payload = {
        'espaco_id': 1,
        'titulo': 'Evento administrativo',
        'descricao': 'Criado por administrador logado.',
        'data_inicio': '2026-12-01T14:00:00',
        'data_fim': '2026-12-01T16:00:00',
    }
    response = client.post('/eventos/', json=payload, headers=authenticated_headers)
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['status'] == 'aceito'


def test_criacao_publica_fica_pendente_mesmo_com_token_enviado(client, authenticated_headers):
    payload = {
        'espaco_id': 1,
        'titulo': 'Evento visitante',
        'descricao': 'Solicitacao feita pelo visitante.',
        'data_inicio': '2026-12-01T14:00:00',
        'data_fim': '2026-12-01T16:00:00',
    }
    response = client.post('/eventos/', json=payload)
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['status'] == 'pendente'


@pytest.mark.parametrize('espaco_id', [2, 3, 4])
def test_eventos_simultaneos_em_espacos_diferentes(client, evento, authenticated_headers, espaco_id):
    payload = client.get('/eventos/').json()['eventos'][0]
    payload['espaco_id'] = espaco_id
    response = client.post('/eventos/', json=payload)
    assert response.status_code == HTTPStatus.CREATED
    evento_id = response.json()['id']
    payload['status'] = 'aceito'
    assert client.put(f'/eventos/{evento_id}', json=payload, headers=authenticated_headers).status_code == HTTPStatus.OK
    payload['espaco_id'] = 1
    assert (
        client.put(f'/eventos/{evento_id}', json=payload, headers=authenticated_headers).status_code
        == HTTPStatus.CONFLICT
    )
    salvo = next(item for item in client.get('/eventos/').json()['eventos'] if item['id'] == evento_id)
    assert salvo['espaco_id'] == espaco_id


@pytest.mark.parametrize('espaco_id', [None, 0, 5, 'ausente'])
def test_espaco_obrigatorio(client, evento, authenticated_headers, espaco_id):
    payload = client.get('/eventos/').json()['eventos'][0]
    if espaco_id == 'ausente':
        payload.pop('espaco_id')
    else:
        payload['espaco_id'] = espaco_id
    assert client.post('/eventos/', json=payload).status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert (
        client.put('/eventos/1', json=payload, headers=authenticated_headers).status_code
        == HTTPStatus.UNPROCESSABLE_ENTITY
    )
