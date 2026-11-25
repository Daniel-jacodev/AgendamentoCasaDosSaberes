from http import HTTPStatus
from io import BytesIO
from json import dumps
from pathlib import Path
from unittest.mock import Mock

import pytest
from reportlab.pdfgen.canvas import Canvas

from app.models.arquivo import ArquivoPDF
from app.models.evento import Evento
from app.services import auth
from app.services import evento as evento_service


def test_cadastro_multipart_salva_pdf_privado(client, session, tmp_path, monkeypatch, administrador):
    privada = tmp_path / 'privada'
    monkeypatch.setattr(evento_service, 'PASTA_PDFS', privada)
    dados = {
        'titulo': 'Mostra cultural',
        'descricao': 'Uma mostra aberta ao público.',
        'espaco_id': 1,
        'data_inicio': '2026-11-20T14:00:00',
        'data_fim': '2026-11-20T16:00:00',
    }
    pdf = BytesIO()
    canvas = Canvas(pdf)
    canvas.drawString(50, 100, 'Portfólio')
    canvas.save()

    resposta = client.post(
        '/eventos/', data={'dados': dumps(dados)}, files={'arquivo': ('mostra.pdf', pdf.getvalue(), 'application/pdf')}
    )

    assert resposta.status_code == HTTPStatus.CREATED
    registro = session.get(ArquivoPDF, resposta.json()['arquivo_pdf_id'])
    arquivo = Path(registro.caminho_local)
    assert arquivo.parent == privada
    assert arquivo.read_bytes() == pdf.getvalue()

    rota = f'/eventos/{resposta.json()["id"]}/proposta'
    assert client.get(rota).status_code == HTTPStatus.UNAUTHORIZED
    download = client.get(rota, headers=administrador)
    assert download.status_code == HTTPStatus.OK
    assert download.headers['Content-Type'] == 'application/pdf'
    assert 'mostra.pdf' in download.headers['Content-Disposition']
    assert download.content == pdf.getvalue()

    fora_da_pasta = tmp_path / 'outro.pdf'
    fora_da_pasta.write_bytes(pdf.getvalue())
    registro.caminho_local = str(fora_da_pasta)
    session.commit()
    assert client.get(rota, headers=administrador).status_code == HTTPStatus.NOT_FOUND


def test_cancelamento_libera_horario_e_reativacao_respeita_conflito(client, evento, authenticated_headers):
    rota = f'/eventos/{evento.id}/status'
    cancelado = client.patch(rota, json={'status': 'cancelado'}, headers=authenticated_headers)
    assert cancelado.status_code == HTTPStatus.OK
    assert cancelado.json()['status'] == 'cancelado'
    assert client.get('/eventos/').json() == {'eventos': []}

    reserva = client.post('/eventos/', json=cancelado.json())
    assert reserva.status_code == HTTPStatus.CREATED
    reativacao = client.patch(rota, json={'status': 'aceito'}, headers=authenticated_headers)
    assert reativacao.status_code == HTTPStatus.CONFLICT


def test_delete_evento(client, evento, session, authenticated_headers):
    evento_id = evento.id

    response = client.delete(f'/eventos/{evento_id}', headers=authenticated_headers)

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b''
    session.expire_all()
    assert session.get(Evento, evento_id) is None
    assert client.get('/eventos/', headers=authenticated_headers).json() == {'eventos': []}
    assert client.delete(f'/eventos/{evento_id}', headers=authenticated_headers).status_code == HTTPStatus.NOT_FOUND


def test_delete_evento_not_found(client, evento, authenticated_headers):
    response = client.delete('/eventos/999', headers=authenticated_headers)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Evento não encontrado.'}
    assert len(client.get('/eventos/', headers=authenticated_headers).json()['eventos']) == 1


def test_get_evento_empty(client, authenticated_headers):
    response = client.get('/eventos/', headers=authenticated_headers)

    assert response.json() == {'eventos': []}


def test_get_evento_populated(client, evento, authenticated_headers):
    response = client.get('/eventos/', headers=authenticated_headers)

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
                'email': None,
                'entidade': None,
                'segmento': None,
                'pauta': None,
                'segmentos': [],
                'pautas': [],
                'origem': None,
                'periodicidade': None,
                'data_fim_recorrencia': None,
                'link_complementar': None,
                'arquivo_pdf_id': None,
                'aceitou_termos': False,
            },
        ]
    }


@pytest.mark.parametrize('rota', ['/eventos/', '/eventos/pendentes', '/eventos/ordenados'])
def test_listar_evento_com_responsavel_legado(client, evento, session, authenticated_headers, rota):
    evento.responsavel = 'oi'
    session.commit()

    response = client.get(rota, headers=authenticated_headers)

    assert response.status_code == HTTPStatus.OK
    (dados,) = response.json()['eventos']
    assert dados['responsavel'] == 'oi'


def test_gravar_evento_com_responsavel_curto(client, evento, authenticated_headers):
    payload = client.get('/eventos/', headers=authenticated_headers).json()['eventos'][0]
    payload['responsavel'] = 'oi'

    assert client.post('/eventos/', json=payload).status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert client.put(f'/eventos/{evento.id}', json=payload, headers=authenticated_headers).status_code == (
        HTTPStatus.UNPROCESSABLE_ENTITY
    )


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
        'aceitou_termos': True,
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
    assert data['aceitou_termos'] is True


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
    def decode_token(token, **_):
        if token == 'valid-token':
            return {'sub': 'user-id'}
        raise ValueError('Token invalido')

    oidc = Mock()
    oidc.decode_token.side_effect = decode_token
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
    eventos = client.get('/eventos/', headers={'Authorization': 'Bearer valid-token'}).json()['eventos']
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
def test_create_evento_conflitante(client, evento, inicio, fim, authenticated_headers):
    payload = {
        'espaco_id': 1,
        'titulo': 'Outro evento',
        'descricao': 'Descricao de outro evento.',
        'data_inicio': inicio,
        'data_fim': fim,
    }
    response = client.post('/eventos/', json=payload)
    assert response.status_code == HTTPStatus.CONFLICT
    assert len(client.get('/eventos/', headers=authenticated_headers).json()['eventos']) == 1


@pytest.mark.parametrize(
    ('inicio', 'fim'),
    [
        ('2026-10-25T10:00:00', '2026-10-25T12:00:00'),
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
        'data_inicio': '2026-10-25T16:00:00',
        'data_fim': '2026-10-25T18:00:00',
    }
    response = client.post('/eventos/', json=payload)
    evento_id = response.json()['id']
    payload.update(data_inicio='2026-10-25T15:00:00', data_fim='2026-10-25T17:00:00')
    response = client.put(f'/eventos/{evento_id}', json=payload, headers=authenticated_headers)
    assert response.status_code == HTTPStatus.CONFLICT
    eventos = client.get('/eventos/', headers=authenticated_headers).json()['eventos']
    atualizado = next(item for item in eventos if item['id'] == evento_id)
    assert atualizado['data_inicio'] == '2026-10-25T16:00:00'


@pytest.mark.parametrize('celular', [None, '(85) 99999-1234', '9' * 30])
def test_cadastro_mvp(client, celular, authenticated_headers):
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
    assert client.get('/eventos/', headers=authenticated_headers).json() == {'eventos': [data]}


def test_aprovacao_persistida(client, evento, session, authenticated_headers):
    data = client.get('/eventos/', headers=authenticated_headers).json()['eventos'][0]
    data.update(status='aceito', celular='(85) 99999-0000')
    response = client.put(f'/eventos/{evento.id}', json=data, headers=authenticated_headers)
    assert response.status_code == HTTPStatus.OK
    assert response.json()['status'] == 'aceito'
    # Recarrega do banco, sem depender do objeto ja carregado pelo ORM.
    session.expire_all()
    assert session.get(Evento, evento.id).status == 'aceito'
    assert session.get(Evento, evento.id).celular == data['celular']
    assert client.get('/eventos/', headers=authenticated_headers).json()['eventos'][0]['status'] == 'aceito'
    response = client.delete(f'/eventos/{evento.id}', headers=authenticated_headers)
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b''
    assert client.get('/eventos/', headers=authenticated_headers).json() == {'eventos': []}


@pytest.mark.parametrize('status', ['recusado', 'confirmando', '', None])
def test_status_invalido(client, evento, authenticated_headers, status):
    data = client.get('/eventos/', headers=authenticated_headers).json()['eventos'][0]
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
def test_aprovacao_recusa_sem_login(client, evento, method, authenticated_headers):
    data = client.get('/eventos/', headers=authenticated_headers).json()['eventos'][0]
    data['status'] = 'aceito'
    response = client.request(method, f'/eventos/{evento.id}', json=data)
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert client.get('/eventos/', headers=authenticated_headers).json()['eventos'][0]['status'] == 'pendente'


def test_criacao_administrativa_aceita_imediatamente(client, authenticated_headers):
    payload = {
        'espaco_id': 1,
        'titulo': 'Evento administrativo',
        'descricao': 'Criado por administrador logado.',
        'email': 'agendamento@example.org',
        'data_inicio': '2026-12-01T14:00:00',
        'data_fim': '2026-12-01T16:00:00',
    }
    response = client.post('/eventos/', json=payload, headers=authenticated_headers)
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['status'] == 'aceito'
    consulta = client.get('/eventos/aceitos')
    assert consulta.status_code == HTTPStatus.OK
    (evento_publico,) = consulta.json()['eventos']
    assert evento_publico['classificacao_indicativa'] is None
    assert 'email' not in evento_publico


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


@pytest.mark.parametrize('espaco_id', [2, 3, 4, 6, 7, 8])
def test_eventos_simultaneos_em_espacos_diferentes(client, evento, authenticated_headers, espaco_id):
    payload = client.get('/eventos/', headers=authenticated_headers).json()['eventos'][0]
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
    eventos = client.get('/eventos/', headers=authenticated_headers).json()['eventos']
    salvo = next(item for item in eventos if item['id'] == evento_id)
    assert salvo['espaco_id'] == espaco_id


@pytest.mark.parametrize('espaco_id', [None, 0, 9, 'ausente'])
def test_espaco_obrigatorio(client, evento, authenticated_headers, espaco_id):
    payload = client.get('/eventos/', headers=authenticated_headers).json()['eventos'][0]
    if espaco_id == 'ausente':
        payload.pop('espaco_id')
    else:
        payload['espaco_id'] = espaco_id
    assert client.post('/eventos/', json=payload).status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert (
        client.put('/eventos/1', json=payload, headers=authenticated_headers).status_code
        == HTTPStatus.UNPROCESSABLE_ENTITY
    )


def test_classificacoes_multiplas_e_origem_sobrevivem_a_decisao_e_edicao_legada(client, authenticated_headers):
    payload = {
        'espaco_id': 5,
        'titulo': 'Sessão noturna',
        'descricao': 'Sessão aberta à comunidade.',
        'data_inicio': '2026-12-01T18:00:00',
        'data_fim': '2026-12-01T21:00:00',
        'segmentos': ['Música', 'Teatro', 'Música'],
        'pautas': ['Social', 'Racial'],
        'origem': 'administrativo',
    }
    resposta = client.post('/eventos/', json=payload)
    assert resposta.status_code == HTTPStatus.CREATED
    evento = resposta.json()
    assert evento['origem'] == 'solicitacao_publica'
    assert evento['segmentos'] == ['Música', 'Teatro']
    assert evento['pautas'] == ['Social', 'Racial']
    rota = f'/eventos/{evento["id"]}'
    assert (
        client.patch(rota + '/status', json={'status': 'aceito'}, headers=authenticated_headers).status_code
        == HTTPStatus.OK
    )
    payload.update(segmento='Música', pauta='Social', status='aceito')
    payload.pop('segmentos')
    payload.pop('pautas')
    atualizado = client.put(rota, json=payload, headers=authenticated_headers).json()
    assert atualizado['origem'] == 'solicitacao_publica'
    assert atualizado['segmentos'] == ['Música', 'Teatro']
    assert atualizado['pautas'] == ['Social', 'Racial']
    assert 'origem' not in client.get('/eventos/aceitos').json()['eventos'][0]


@pytest.mark.parametrize(
    ('espaco', 'inicio', 'fim'),
    [
        (5, '2026-12-01T14:00:00', '2026-12-01T16:00:00'),
        (1, '2026-12-01T18:00:00', '2026-12-01T20:00:00'),
        (1, '2026-12-01T11:00:00', '2026-12-01T13:00:00'),
        (1, '2026-12-01T14:00:00', '2026-12-01T15:00:00'),
        (1, '2026-12-01T08:00:00', '2026-12-01T12:00:00'),
        (1, '2026-09-01T14:00:00', '2026-09-01T16:00:00'),
    ],
)
def test_gravacao_evento_recusa_periodos_fora_da_disponibilidade(client, espaco, inicio, fim):
    resposta = client.post(
        '/eventos/',
        json={
            'titulo': 'Evento de teste',
            'descricao': 'Atividade aberta à comunidade.',
            'espaco_id': espaco,
            'data_inicio': inicio,
            'data_fim': fim,
        },
    )
    assert resposta.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_salas_e_corredor_sao_independentes_e_preservam_reservas_legadas(client, authenticated_headers):
    payload = {
        'titulo': 'Exposição de arte',
        'descricao': 'Atividade aberta à comunidade.',
        'data_inicio': '2026-12-01T14:00:00',
        'data_fim': '2026-12-01T16:00:00',
    }

    def gravar(espaco_id):
        return client.post('/eventos/', json={**payload, 'espaco_id': espaco_id})

    def bloqueios(espaco_id):
        resposta = client.get('/disponibilidade', params={'data': '2026-12-01', 'espaco_id': espaco_id})
        assert resposta.status_code == HTTPStatus.OK
        return resposta.json()['bloqueios']

    legado = gravar(3)
    assert legado.status_code == HTTPStatus.CREATED
    assert bloqueios(6) == bloqueios(7) == [{'data_inicio': '2026-12-01T14:00:00', 'data_fim': '2026-12-01T16:00:00'}]
    assert bloqueios(8) == []
    assert gravar(6).status_code == HTTPStatus.CONFLICT
    assert gravar(7).status_code == HTTPStatus.CONFLICT
    assert gravar(8).status_code == HTTPStatus.CREATED

    cancelada = client.patch(
        f'/eventos/{legado.json()["id"]}/status', json={'status': 'cancelado'}, headers=authenticated_headers
    )
    assert cancelada.status_code == HTTPStatus.OK
    assert bloqueios(6) == bloqueios(7) == []
    assert gravar(6).status_code == HTTPStatus.CREATED
    assert bloqueios(7) == []
    assert gravar(7).status_code == HTTPStatus.CREATED
    assert gravar(3).status_code == HTTPStatus.CONFLICT

    for espaco_id in (6, 7, 8):
        assert bloqueios(espaco_id)
        assert gravar(espaco_id).status_code == HTTPStatus.CONFLICT
