from datetime import datetime, timedelta
from http import HTTPStatus

import pytest

from app.models.evento import Evento, PautaEnum
from app.models.visita import NaturezaInstituicaoEnum, Visita
from app.schemas.relatorio import FiltroRelatorio
from app.services import auth
from app.services.relatorio import consultar_relatorio

ROTA = '/relatorios/agendamentos'
FILTRO = {'tipo': 'ambos', 'data_inicio': '2026-11-23', 'data_fim': '2026-11-24'}


@pytest.fixture
def administrador(monkeypatch):
    monkeypatch.setattr(auth, 'validar_token_keycloak', lambda _: {'realm_access': {'roles': ['administrador']}})
    return {'Authorization': 'Bearer admin-token'}


@pytest.fixture
def agenda(session):
    for titulo, inicio, status, pauta, publico in (
        ('Abertura', datetime(2026, 11, 23), 'aceito', PautaEnum.SOCIAL, 40),
        ('Arte & Memória <UFC>', datetime(2026, 11, 24, 23, 59, 59, 999999), 'aceito', None, 100),
        ('Sem estimativa', datetime(2026, 11, 24, 9), 'aceito', PautaEnum.SOCIAL, None),
        ('Em avaliação', datetime(2026, 11, 24, 13), 'pendente', PautaEnum.RACIAL, 300),
        ('Antes do período', datetime(2026, 11, 22, 23), 'aceito', None, 900),
        ('Depois do período', datetime(2026, 11, 25), 'aceito', None, 800),
    ):
        session.add(
            Evento(
                titulo=titulo,
                descricao='Descrição do evento.',
                data_inicio=inicio,
                data_fim=inicio + timedelta(hours=2),
                espaco_id=1,
                status=status,
                pauta=pauta,
                publico_estimado=publico,
            )
        )
    session.add(
        Visita(
            nome_responsavel='Responsável',
            email='responsavel@example.com',
            telefone='85999999999',
            quantidade_pessoas=30,
            possui_pcd=True,
            natureza_instituicao=NaturezaInstituicaoEnum.PUBLICA,
            data_inicio=datetime(2026, 11, 23, 14),
            data_fim=datetime(2026, 11, 23, 16),
            status='aprovada',
        )
    )
    session.commit()


def test_metricas_do_periodo(session, agenda):
    eventos, visitas = consultar_relatorio(session, FiltroRelatorio.model_validate(FILTRO))

    assert (eventos.confirmados, eventos.pendentes) == (3, 1)
    assert eventos.dias == {0: 1, 1: 2}
    assert eventos.horarios == {0: 1, 9: 1, 23: 1}
    assert eventos.pautas == {'Social': 2, 'Não informada': 1}
    assert (eventos.publico_estimado, eventos.eventos_com_estimativa) == (140, 2)
    assert [evento.titulo for evento in eventos.ranking] == ['Arte & Memória <UFC>', 'Abertura']

    assert (visitas.confirmados, visitas.pendentes) == (1, 0)
    assert visitas.horarios == {14: 1}
    assert visitas.instituicoes == {'Pública': 1}
    assert (visitas.pessoas_previstas, visitas.grupos_com_pcd) == (30, 1)


@pytest.mark.parametrize(('tipo', 'paginas'), [('eventos', 1), ('visitas', 1), ('ambos', 2)])
def test_download_pdf(client, administrador, agenda, tipo, paginas):
    resposta = client.get(ROTA, params={**FILTRO, 'tipo': tipo}, headers=administrador)

    assert resposta.status_code == HTTPStatus.OK
    assert resposta.headers['Content-Type'] == 'application/pdf'
    assert (
        resposta.headers['Content-Disposition']
        == f'attachment; filename="relatorio-{tipo}-2026-11-23-a-2026-11-24.pdf"'
    )
    assert resposta.content.startswith(b'%PDF-')
    assert resposta.content.count(b'/Type /Page\n') == paginas


def test_periodo_de_um_dia_sem_dados(client, administrador):
    resposta = client.get(ROTA, params={**FILTRO, 'data_fim': FILTRO['data_inicio']}, headers=administrador)
    assert resposta.status_code == HTTPStatus.OK
    assert resposta.content.startswith(b'%PDF-')


@pytest.mark.parametrize('alteracao', [{'tipo': 'outro'}, {'data_inicio': 'ontem'}, {'data_fim': '2026-11-22'}])
def test_filtro_invalido(client, administrador, alteracao):
    resposta = client.get(ROTA, params={**FILTRO, **alteracao}, headers=administrador)
    assert resposta.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_relatorio_exige_papel_administrador(client, authenticated_headers):
    assert client.get(ROTA, params=FILTRO).status_code == HTTPStatus.UNAUTHORIZED
    assert client.get(ROTA, params=FILTRO, headers=authenticated_headers).status_code == HTTPStatus.FORBIDDEN
