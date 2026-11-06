from http import HTTPStatus

from app.models.evento import Evento


def test_delete_evento(client, evento, session):
    evento_id = evento.id

    response = client.delete(f'/eventos/{evento_id}')

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b''
    session.expire_all()
    assert session.get(Evento, evento_id) is None
    assert client.get('/eventos/').json() == {'eventos': []}
    assert client.delete(f'/eventos/{evento_id}').status_code == HTTPStatus.NOT_FOUND


def test_delete_evento_not_found(client, evento):
    response = client.delete('/eventos/999')

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


def test_update_evento(client, evento):
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

    response = client.put('/eventos/1', json=payload)

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


def test_update_evento_not_found(client, evento):
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

    response = client.put('/eventos/999', json=payload)

    assert response.status_code == HTTPStatus.NOT_FOUND
