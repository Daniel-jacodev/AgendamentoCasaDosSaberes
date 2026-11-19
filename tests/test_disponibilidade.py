from datetime import datetime
from http import HTTPStatus

from app.models.evento import Evento


def test_disponibilidade_por_espaco_e_data(client, session):
    session.add_all([
        Evento(
            titulo='Reserva pendente',
            descricao='Dados da solicitação',
            espaco_id=1,
            data_inicio=datetime(2026, 11, 19, 23),
            data_fim=datetime(2026, 11, 20, 9),
        ),
        Evento(
            titulo='Reserva confirmada',
            descricao='Dados da confirmação',
            espaco_id=1,
            status='aceito',
            data_inicio=datetime(2026, 11, 20, 9),
            data_fim=datetime(2026, 11, 20, 10),
        ),
        Evento(
            titulo='Reserva da tarde',
            descricao='Dados da solicitação da tarde',
            espaco_id=1,
            data_inicio=datetime(2026, 11, 20, 15),
            data_fim=datetime(2026, 11, 20, 16),
        ),
        Evento(
            titulo='Reserva de outro espaço',
            descricao='Dados da outra solicitação',
            espaco_id=2,
            data_inicio=datetime(2026, 11, 20, 14),
            data_fim=datetime(2026, 11, 20, 16),
        ),
    ])
    session.commit()

    response = client.get('/disponibilidade', params={'data': '2026-11-20', 'espaco_id': 1})
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        'data': '2026-11-20',
        'espaco_id': 1,
        'duracao_minima_horas': 2,
        'duracao_maxima_horas': 3,
        'bloqueios': [
            {'data_inicio': '2026-11-20T00:00:00', 'data_fim': '2026-11-20T10:00:00'},
            {'data_inicio': '2026-11-20T15:00:00', 'data_fim': '2026-11-20T16:00:00'},
        ],
        'horarios_reservaveis': [
            {'data_inicio': '2026-11-20T10:00:00', 'data_fim': '2026-11-20T12:00:00'},
            {'data_inicio': '2026-11-20T16:00:00', 'data_fim': '2026-11-20T18:00:00'},
        ],
    }
    externa = client.get('/disponibilidade', params={'data': '2026-11-20', 'espaco_id': 5})
    assert externa.json()['horarios_reservaveis'] == [
        {'data_inicio': '2026-11-20T18:00:00', 'data_fim': '2026-11-20T21:00:00'},
    ]
