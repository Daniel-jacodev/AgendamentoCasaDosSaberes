from http import HTTPStatus

import pytest

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
        'data_fim': '2026-11-20T15:00:00',
        'observacoes': 'Visita mediada para turma universitária.',
    }


def test_criar_visita_admin(client, administrador):
    payload = payload_visita()
    payload.update(formacao='Pedagogia', possui_pcd=True, quantidade_pcd=2)
    response = client.post(
        '/visitas/',
        json=payload,
        headers=administrador,
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

    consulta = client.get('/visitas/', headers=administrador)
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


def test_cancelar_pela_rota_legada_preserva_a_visita(client, administrador):
    criada = client.post('/visitas/', json=payload_visita(), headers=administrador).json()
    resposta = client.delete(f'/visitas/{criada["id"]}', headers=administrador)
    assert resposta.status_code == HTTPStatus.NO_CONTENT
    assert client.get('/visitas/', headers=administrador).json()['visitas'][0]['status'] == 'cancelada'


def test_cancelar_visita_inexistente_pela_rota_legada(client, administrador):
    resposta = client.delete('/visitas/999', headers=administrador)
    assert resposta.status_code == HTTPStatus.NOT_FOUND
    assert resposta.json() == {'detail': 'Visita não encontrada.'}


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


def test_disponibilidade_e_conflito_de_visita_pendente(client, session, administrador):
    dados = VisitaCreate.model_validate({**payload_visita(), 'data_fim': '2026-11-20T16:00:00'})
    session.add(Visita(**dados.model_dump(), status=StatusVisitaEnum.PENDENTE.value))
    session.commit()

    consulta = client.get('/visitas/disponibilidade', params={'data': '2026-11-20'})
    assert consulta.status_code == HTTPStatus.OK
    assert consulta.json() == {
        'data': '2026-11-20',
        'bloqueios': [{'data_inicio': '2026-11-20T14:00:00', 'data_fim': '2026-11-20T16:00:00'}],
        'horarios_reservaveis': [
            {'data_inicio': '2026-11-20T08:00:00', 'data_fim': '2026-11-20T12:00:00'},
            {'data_inicio': '2026-11-20T16:00:00', 'data_fim': '2026-11-20T18:00:00'},
        ],
    }

    payload = payload_visita()
    payload.update(data_inicio='2026-11-20T18:00:00Z', data_fim='2026-11-20T19:00:00Z')
    conflito = client.post('/visitas/', json=payload, headers=administrador)
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

    payload.update(data_inicio='2026-11-20T19:00:00Z', data_fim='2026-11-20T17:00:00-03:00')
    consecutiva = client.post('/visitas/', json=payload, headers=administrador)
    assert consecutiva.status_code == HTTPStatus.CREATED
    assert consecutiva.json()['data_inicio'] == '2026-11-20T16:00:00'
    assert client.post('/visitas/', json=payload, headers=administrador).status_code == HTTPStatus.CONFLICT
    consultas = client.get('/visitas/', headers=administrador)
    assert [visita['status'] for visita in consultas.json()['visitas']] == ['pendente', 'aprovada']


def test_decisao_de_visita_exige_admin_e_cancelamento_libera_sem_apagar(client, session, administrador, monkeypatch):
    visita = client.post('/visitas/', json=payload_visita()).json()
    rota = f'/visitas/{visita["id"]}/status'
    assert client.patch(rota, json={'status': 'aprovada'}).status_code == HTTPStatus.UNAUTHORIZED
    with monkeypatch.context() as permissoes:
        permissoes.setattr('app.services.auth.validar_token_keycloak', lambda _: {'sub': 'visitante'})
        assert (
            client.patch(rota, json={'status': 'aprovada'}, headers=administrador).status_code == HTTPStatus.FORBIDDEN
        )

    aprovada = client.patch(rota, json={'status': 'aprovada'}, headers=administrador)
    assert aprovada.status_code == HTTPStatus.OK
    assert client.get('/visitas/aceitas').json()['visitas'][0]['id'] == visita['id']
    assert client.patch(rota, json={'status': 'negada'}, headers=administrador).status_code == HTTPStatus.CONFLICT
    for _ in range(2):
        assert client.patch(rota, json={'status': 'cancelada'}, headers=administrador).json()['status'] == 'cancelada'
    session.expire_all()
    assert session.get(Visita, visita['id']).status == 'cancelada'
    assert client.get('/visitas/aceitas').json() == {'visitas': []}
    assert client.get('/visitas/disponibilidade?data=2026-11-20').json()['bloqueios'] == []
    nova = client.post('/visitas/', json=payload_visita())
    assert nova.status_code == HTTPStatus.CREATED
    negativa = client.patch(f'/visitas/{nova.json()["id"]}/status', json={'status': 'negada'}, headers=administrador)
    assert negativa.json()['status'] == 'negada'
    assert client.post('/visitas/', json=payload_visita()).status_code == HTTPStatus.CREATED


@pytest.mark.parametrize(
    ('inicio', 'fim'),
    [
        ('2026-11-20T11:30:00', '2026-11-20T12:30:00'),
        ('2026-11-20T14:00:00', '2026-11-20T16:00:00'),
        ('2026-09-01T08:00:00', '2026-09-01T09:00:00'),
    ],
)
def test_visita_recusa_horario_invalido(client, inicio, fim):
    assert (
        client.post('/visitas/', json={**payload_visita(), 'data_inicio': inicio, 'data_fim': fim}).status_code
        == HTTPStatus.UNPROCESSABLE_ENTITY
    )
