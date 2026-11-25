from http import HTTPStatus
from json import dumps

import pytest

from app.schemas.relatorio import FiltroRelatorio
from app.services import evento as evento_service
from app.services.relatorio import consultar_relatorio

ROTA_EVENTOS = '/eventos/'
EVENTO = {
    'titulo': 'Mostra cultural',
    'descricao': 'Uma mostra aberta ao público.',
    'espaco_id': 1,
    'data_inicio': '2026-11-20T14:00:00',
    'data_fim': '2026-11-20T16:00:00',
}


@pytest.mark.parametrize('periodicidade', ['Semanal', 'Mensal'])
def test_recorrencia_exige_data_final_valida(client, periodicidade):
    dados = {**EVENTO, 'periodicidade': periodicidade}
    assert client.post(ROTA_EVENTOS, json=dados).status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    dados['data_fim_recorrencia'] = '2026-11-19'
    assert client.post(ROTA_EVENTOS, json=dados).status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_serie_semanal_conflita_ao_aprovar_e_bloqueia_agenda_apos_aceite(client, authenticated_headers):
    serie = {**EVENTO, 'periodicidade': 'Semanal', 'data_fim_recorrencia': '2026-12-04'}
    pedido = client.post(ROTA_EVENTOS, json=serie)
    assert pedido.status_code == HTTPStatus.CREATED
    serie_id = pedido.json()['id']
    rota = f'/eventos/{serie_id}/status'
    outro = {**EVENTO, 'data_inicio': '2026-11-27T15:00:00', 'data_fim': '2026-11-27T17:00:00'}
    parametros = {'espaco_id': 1, 'data': '2026-11-27'}
    assert client.get('/eventos/aceitos').json()['eventos'] == []
    assert client.get('/disponibilidade', params=parametros).json()['bloqueios'] == []

    reserva = client.post(ROTA_EVENTOS, json=outro)
    assert reserva.status_code == HTTPStatus.CREATED
    conflito = client.patch(rota, json={'status': 'aceito'}, headers=authenticated_headers)
    assert conflito.status_code == HTTPStatus.CONFLICT
    assert '27/11/2026' in conflito.json()['detail']
    pendentes = client.get('/eventos/pendentes', headers=authenticated_headers).json()['eventos']
    assert serie_id in {item['id'] for item in pendentes}

    client.delete(f'/eventos/{reserva.json()["id"]}', headers=authenticated_headers)
    for _ in range(2):
        assert client.patch(rota, json={'status': 'aceito'}, headers=authenticated_headers).status_code == HTTPStatus.OK
    agenda = client.get('/eventos/aceitos').json()['eventos']
    assert [item['data_inicio'] for item in agenda] == [
        '2026-11-20T14:00:00',
        '2026-11-27T14:00:00',
        '2026-12-04T14:00:00',
    ]
    assert {item['id'] for item in agenda} == {serie_id}
    assert len({item['ocorrencia_id'] for item in agenda}) == len(agenda)
    assert client.get('/disponibilidade', params=parametros).json()['bloqueios'] == [
        {'data_inicio': '2026-11-27T14:00:00', 'data_fim': '2026-11-27T16:00:00'}
    ]
    assert client.post(ROTA_EVENTOS, json=outro).status_code == HTTPStatus.CONFLICT
    assert client.patch(rota, json={'status': 'cancelado'}, headers=authenticated_headers).status_code == HTTPStatus.OK
    assert client.get('/eventos/aceitos').json()['eventos'] == []
    assert client.get('/disponibilidade', params=parametros).json()['bloqueios'] == []


def test_recorrencia_mensal_e_relatorio_de_periodo_posterior(client, session, authenticated_headers):
    dados = {
        **EVENTO,
        'periodicidade': 'Mensal',
        'data_fim_recorrencia': '2027-03-31',
        'data_inicio': '2027-01-31T14:00:00',
        'data_fim': '2027-01-31T16:00:00',
    }
    resposta = client.post(ROTA_EVENTOS, json=dados, headers=authenticated_headers)
    assert resposta.status_code == HTTPStatus.CREATED
    agenda = client.get(ROTA_EVENTOS).json()['eventos']
    assert [item['data_inicio'] for item in agenda] == [
        '2027-01-31T14:00:00',
        '2027-02-28T14:00:00',
        '2027-03-31T14:00:00',
    ]
    filtro = FiltroRelatorio.model_validate({'tipo': 'eventos', 'data_inicio': '2027-02-01', 'data_fim': '2027-03-31'})
    resumo, _ = consultar_relatorio(session, filtro)
    assert (resumo.confirmados, resumo.horarios) == (2, {14: 2})

    alteracao = {
        **dados,
        'status': 'aceito',
        'data_fim_recorrencia': '2027-02-28',
    }
    resposta = client.put(f'/eventos/{resposta.json()["id"]}', json=alteracao, headers=authenticated_headers)
    assert resposta.status_code == HTTPStatus.OK
    assert [item['data_inicio'] for item in client.get(ROTA_EVENTOS).json()['eventos']] == [
        '2027-01-31T14:00:00',
        '2027-02-28T14:00:00',
    ]


@pytest.mark.parametrize(
    ('tamanho', 'status'),
    [(None, HTTPStatus.CREATED), (3_145_728, HTTPStatus.CREATED), (3_145_729, HTTPStatus.BAD_REQUEST)],
)
def test_pdf_opcional_tem_limite_de_tres_mb(client, tmp_path, monkeypatch, tamanho, status):
    monkeypatch.setattr(evento_service, 'PASTA_PDFS', tmp_path)
    campos = {'dados': (None, dumps(EVENTO))}
    if tamanho is not None:
        conteudo = b'%PDF-1.7\n' + b' ' * (tamanho - len(b'%PDF-1.7\n'))
        campos['arquivo'] = ('mostra.pdf', conteudo, 'application/pdf')

    resposta = client.post(ROTA_EVENTOS, files=campos)

    assert resposta.status_code == status
    if tamanho is None:
        assert resposta.json()['arquivo_pdf_id'] is None
    if status == HTTPStatus.BAD_REQUEST:
        assert '3 MB' in resposta.json()['detail']
        assert list(tmp_path.iterdir()) == []
