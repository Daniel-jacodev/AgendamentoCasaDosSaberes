from http import HTTPStatus

from app.models.visita import StatusVisitaEnum, Visita
from app.schemas.visita import VisitaCreate


def payload_visita():
    return {
        'nome_responsavel': 'Carlos Eduardo',
        'email': 'carlos@email.com',
        'telefone': '(85) 99999-9999',
        'instituicao': 'UFC',
        'quantidade_pessoas': 20,
        'data_inicio': '2026-11-20T14:00:00',
        'data_fim': '2026-11-20T16:00:00',
        'observacoes': 'Visita mediada para turma universitária.',
    }


def test_criar_visita_admin(client, authenticated_headers):
    payload = payload_visita()
    payload.update(formacao='Pedagogia', possui_pcd=True, quantidade_pcd=2)
    response = client.post(
        '/visitas/',
        json=payload,
        headers=authenticated_headers,
    )

    assert response.status_code == HTTPStatus.CREATED

    data = response.json()

    assert data['id'] == 1
    assert data['status'] == 'aprovada'
    assert data['nome_responsavel'] == 'Carlos Eduardo'
    assert data['email'] == 'carlos@email.com'
    assert data['quantidade_pessoas'] == payload['quantidade_pessoas']
    assert data['formacao'] == payload['formacao']
    assert data['quantidade_pcd'] == payload['quantidade_pcd']

    consulta = client.get('/visitas/', headers=authenticated_headers)
    assert consulta.json() == {'visitas': [data]}
    consulta_publica = client.get('/visitas/aceitas')
    assert consulta_publica.json() == {
        'visitas': [{campo: data[campo] for campo in ('id', 'status', 'data_inicio', 'data_fim')}]
    }


def test_criar_visita_sem_autenticacao(client):
    response = client.post(
        '/visitas/',
        json={**payload_visita(), 'status': 'aprovada'},
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['status'] == 'pendente'
    assert client.get('/visitas/aceitas').json() == {'visitas': []}


def test_deletar_visita_admin(client, authenticated_headers):
    create_response = client.post(
        '/visitas/',
        json=payload_visita(),
        headers=authenticated_headers,
    )

    visita_id = create_response.json()['id']

    response = client.delete(
        f'/visitas/{visita_id}',
        headers=authenticated_headers,
    )

    assert response.status_code == HTTPStatus.NO_CONTENT


def test_deletar_visita_inexistente(client, authenticated_headers):
    response = client.delete(
        '/visitas/999',
        headers=authenticated_headers,
    )

    assert response.status_code == HTTPStatus.NOT_FOUND

    assert response.json() == {'detail': 'Visita não encontrada.'}


def test_deletar_visita_sem_autenticacao(client):
    response = client.delete(
        '/visitas/1',
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_criar_visita_periodo_invalido(client, authenticated_headers):
    payload = payload_visita()
    payload['data_inicio'] = '2026-11-20T16:00:00'
    payload['data_fim'] = '2026-11-20T14:00:00'

    response = client.post(
        '/visitas/',
        json=payload,
        headers=authenticated_headers,
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_disponibilidade_e_conflito_de_visita_pendente(client, session, authenticated_headers):
    dados = VisitaCreate.model_validate(payload_visita())
    session.add(Visita(**dados.model_dump(), status=StatusVisitaEnum.PENDENTE.value))
    session.commit()

    consulta = client.get('/visitas/disponibilidade', params={'data': '2026-11-20'})
    assert consulta.status_code == HTTPStatus.OK
    assert consulta.json() == {
        'data': '2026-11-20',
        'bloqueios': [{'data_inicio': '2026-11-20T14:00:00', 'data_fim': '2026-11-20T16:00:00'}],
        'horarios_reservaveis': [
            {'data_inicio': '2026-11-20T08:00:00', 'data_fim': '2026-11-20T12:00:00'},
            {'data_inicio': '2026-11-20T13:30:00', 'data_fim': '2026-11-20T14:00:00'},
            {'data_inicio': '2026-11-20T16:00:00', 'data_fim': '2026-11-20T18:00:00'},
        ],
    }

    payload = payload_visita()
    payload.update(data_inicio='2026-11-20T18:00:00Z', data_fim='2026-11-20T20:00:00Z')
    conflito = client.post('/visitas/', json=payload, headers=authenticated_headers)
    assert conflito.status_code == HTTPStatus.CONFLICT
    assert conflito.json() == {'detail': 'Horário indisponível para visita. Escolha outro horário.'}

    evento = client.post(
        '/eventos/',
        json={
            'titulo': 'Evento paralelo',
            'descricao': 'Descrição do evento paralelo.',
            'espaco_id': 1,
            'data_inicio': '2026-11-20T16:00:00',
            'data_fim': '2026-11-20T18:00:00',
        },
    )
    assert evento.status_code == HTTPStatus.CREATED

    payload.update(data_inicio='2026-11-20T19:00:00Z', data_fim='2026-11-20T18:00:00-03:00')
    consecutiva = client.post('/visitas/', json=payload, headers=authenticated_headers)
    assert consecutiva.status_code == HTTPStatus.CREATED
    assert consecutiva.json()['data_inicio'] == '2026-11-20T16:00:00'
    assert client.post('/visitas/', json=payload, headers=authenticated_headers).status_code == HTTPStatus.CONFLICT
    consultas = client.get('/visitas/', headers=authenticated_headers)
    assert [visita['status'] for visita in consultas.json()['visitas']] == ['pendente', 'aprovada']
