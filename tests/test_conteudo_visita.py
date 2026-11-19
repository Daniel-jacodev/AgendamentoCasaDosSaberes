from http import HTTPStatus
from unittest.mock import Mock

import pytest

from app.services import auth


@pytest.fixture
def admin_headers(monkeypatch):
    oidc = Mock()
    oidc.decode_token.return_value = {'sub': 'admin-id', 'realm_access': {'roles': ['administrador']}}
    monkeypatch.setattr(auth, 'criar_openid_keycloak', lambda: oidc)
    return {'Authorization': 'Bearer admin-token'}


def test_publicar_editar_pausar_e_reativar_exposicao(client, admin_headers):
    assert client.get('/exposicoes/').json() == {'exposicoes': []}
    rota = '/exposicoes/2'

    publicacao = client.put(rota, json={'nome': 'Memórias do Sertão'}, headers=admin_headers)
    assert publicacao.status_code == HTTPStatus.OK
    assert publicacao.json() == {
        'sala_id': 2,
        'nome': 'Memórias do Sertão',
        'descricao': '',
        'classificacao': '',
        'pausada': False,
    }
    client.put('/exposicoes/4', json={'nome': 'Fotografia'}, headers=admin_headers)

    pausa = client.put(f'{rota}/status', json={'pausada': True}, headers=admin_headers)
    assert pausa.status_code == HTTPStatus.OK
    assert pausa.json()['pausada'] is True
    assert [item['sala_id'] for item in client.get('/exposicoes/').json()['exposicoes']] == [4]

    edicao = client.put(rota, json={'nome': 'Memórias', 'classificacao': 'Livre'}, headers=admin_headers)
    assert edicao.status_code == HTTPStatus.OK
    assert edicao.json()['pausada'] is True
    painel = client.get('/exposicoes/administracao', headers=admin_headers)
    assert painel.status_code == HTTPStatus.OK
    assert [sala['id'] for sala in painel.json()['salas']] == [1, 2, 3, 4]
    assert painel.json()['exposicoes'][0] == edicao.json()

    reativada = client.put(f'{rota}/status', json={'pausada': False}, headers=admin_headers)
    assert reativada.status_code == HTTPStatus.OK
    assert client.get('/exposicoes/').json()['exposicoes'][0] == reativada.json()


def test_salvar_exposicao_com_status_no_mesmo_pedido(client, admin_headers):
    rota = '/exposicoes/1'
    pausada = client.put(rota, json={'nome': 'Memórias', 'pausada': True}, headers=admin_headers)
    assert pausada.status_code == HTTPStatus.OK
    assert pausada.json()['pausada'] is True
    assert client.get('/exposicoes/').json() == {'exposicoes': []}

    ativa = client.put(rota, json={'nome': 'Memórias da Casa', 'pausada': False}, headers=admin_headers)
    assert ativa.status_code == HTTPStatus.OK
    assert client.get('/exposicoes/').json() == {'exposicoes': [ativa.json()]}


@pytest.mark.parametrize(
    ('rota', 'conteudo', 'status'),
    [
        ('/exposicoes/5', {'nome': 'Memórias'}, HTTPStatus.NOT_FOUND),
        ('/exposicoes/1/status', {'pausada': True}, HTTPStatus.NOT_FOUND),
        ('/exposicoes/1', {'nome': '   '}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ('/exposicoes/1', {'nome': 'Memórias', 'descricao': 'x' * 501}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ('/exposicoes/1/status', {'pausada': 'true'}, HTTPStatus.UNPROCESSABLE_ENTITY),
    ],
)
def test_validacao_exposicao(client, admin_headers, rota, conteudo, status):
    assert client.put(rota, json=conteudo, headers=admin_headers).status_code == status


def test_salvar_configuracao_formulario(client, admin_headers):
    rota = '/visitas/formulario'
    padrao = client.get(rota)
    assert padrao.status_code == HTTPStatus.OK
    assert padrao.json()['campos'][0]['id'] == 'responsavel'

    campos = {
        'campos': [
            {'id': 'instituicao', 'titulo': 'Instituição', 'opcoes': ['Escola', 'Outro'], 'outro': True},
            {'id': 'objetivo', 'titulo': 'Objetivo da visita', 'opcional': True, 'complementar': True},
        ]
    }
    salvo = client.put(rota, json=campos, headers=admin_headers)
    assert salvo.status_code == HTTPStatus.OK
    assert salvo.json() == campos
    assert client.get(rota).json() == campos

    sem_perguntas = {'campos': []}
    assert client.put(rota, json=sem_perguntas, headers=admin_headers).status_code == HTTPStatus.OK
    assert client.get(rota).json() == sem_perguntas


@pytest.mark.parametrize(
    'campos',
    [
        [{'id': 'grupo', 'titulo': 'Grupo'}, {'id': 'grupo', 'titulo': 'Outra pergunta'}],
        [{'id': 'grupo', 'titulo': '   '}],
        [{'id': 'grupo', 'titulo': 'Grupo', 'opcoes': []}],
        [{'id': 'grupo', 'titulo': 'Grupo', 'opcoes': ['   ']}],
    ],
)
def test_rejeitar_formulario_invalido(client, admin_headers, campos):
    rota = '/visitas/formulario'
    padrao = client.get(rota).json()
    assert (
        client.put(rota, json={'campos': campos}, headers=admin_headers).status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    )
    assert client.get(rota).json() == padrao


@pytest.mark.parametrize(
    ('metodo', 'rota', 'conteudo'),
    [
        ('GET', '/exposicoes/administracao', None),
        ('PUT', '/exposicoes/1', {'nome': 'Memórias'}),
        ('PUT', '/exposicoes/1/status', {'pausada': True}),
        ('PUT', '/visitas/formulario', {'campos': []}),
    ],
)
def test_rotas_administrativas_exigem_papel(client, authenticated_headers, metodo, rota, conteudo):
    assert client.request(metodo, rota, json=conteudo).status_code == HTTPStatus.UNAUTHORIZED
    resposta = client.request(metodo, rota, json=conteudo, headers=authenticated_headers)
    assert resposta.status_code == HTTPStatus.FORBIDDEN
