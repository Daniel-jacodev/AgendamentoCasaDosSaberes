from http import HTTPStatus


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
                'descricao': 'Uma oficina prática focada no ensino de respiração, dedilhado e '
                'ornamentações básicas.',
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
