from datetime import date, datetime, time, timedelta

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.constants.espacos import ESPACO_AREA_EXTERNA_ID
from app.constants.horarios import (
    DURACAO_MAXIMA_HORAS,
    DURACAO_MINIMA_HORAS,
    FIM_EXPEDIENTE,
    FIM_EXPEDIENTE_NOTURNO,
    FIM_INTERVALO,
    INICIO_EXPEDIENTE,
    INICIO_INTERVALO,
)
from app.models.evento import STATUS_EVENTO_ATIVO, Evento
from app.models.visita import STATUS_VISITA_ATIVA, Visita
from app.schemas.disponibilidade import DisponibilidadeEspacoResponse, DisponibilidadeVisitaResponse, Periodo
from app.services import horario_service

type Agenda = type[Evento] | type[Visita]

TURNOS_DIURNOS = ((INICIO_EXPEDIENTE, INICIO_INTERVALO), (FIM_INTERVALO, FIM_EXPEDIENTE))
TURNO_NOTURNO = ((FIM_EXPEDIENTE, FIM_EXPEDIENTE_NOTURNO),)
DURACAO_MINIMA_EVENTO = timedelta(hours=DURACAO_MINIMA_HORAS)
DURACAO_MAXIMA_EVENTO = timedelta(hours=DURACAO_MAXIMA_HORAS)
DURACAO_VISITA = timedelta(hours=1)


def _turnos_espaco(espaco_id: int):
    return TURNO_NOTURNO if espaco_id == ESPACO_AREA_EXTERNA_ID else TURNOS_DIURNOS


def _validar_horario(inicio: datetime, fim: datetime, turnos, minimo: timedelta, maximo: timedelta) -> None:
    if inicio <= horario_service.agora_local():
        raise HTTPException(422, 'Escolha um horário futuro.')
    if not minimo <= fim - inicio <= maximo:
        detalhe = (
            'A visita deve durar 1 hora.'
            if minimo == maximo
            else f'O evento deve durar entre {DURACAO_MINIMA_HORAS} e {DURACAO_MAXIMA_HORAS} horas.'
        )
        raise HTTPException(422, detalhe)
    if inicio.date() != fim.date() or not any(
        abertura <= inicio.time() < fim.time() <= fechamento for abertura, fechamento in turnos
    ):
        raise HTTPException(422, 'Escolha um período inteiro dentro do horário de funcionamento.')


def validar_horario_evento(inicio: datetime, fim: datetime, espaco_id: int) -> None:
    _validar_horario(inicio, fim, _turnos_espaco(espaco_id), DURACAO_MINIMA_EVENTO, DURACAO_MAXIMA_EVENTO)


def validar_horario_visita(inicio: datetime, fim: datetime) -> None:
    _validar_horario(inicio, fim, TURNOS_DIURNOS, DURACAO_VISITA, DURACAO_VISITA)


def sobreposicao(agenda: Agenda, inicio: datetime, fim: datetime):
    return (agenda.data_inicio < fim, agenda.data_fim > inicio)


def bloquear_agenda(db: Session, agenda: Agenda) -> None:
    # O bloqueio também serializa inserções quando ainda não há reservas.
    if db.get_bind().dialect.name == 'postgresql':
        db.execute(text(f'LOCK TABLE {agenda.__tablename__} IN SHARE ROW EXCLUSIVE MODE'))


def _bloqueios_do_dia(db: Session, data: date, espaco_id: int | None) -> list[Periodo]:
    inicio = datetime.combine(data, time.min)
    fim = datetime.max if data == date.max else inicio + timedelta(days=1)
    agenda = Visita if espaco_id is None else Evento
    query = select(agenda.data_inicio, agenda.data_fim).where(*sobreposicao(agenda, inicio, fim))
    if espaco_id is None:
        query = query.where(Visita.status.in_(STATUS_VISITA_ATIVA))
    else:
        query = query.where(Evento.espaco_id == espaco_id, Evento.status.in_(STATUS_EVENTO_ATIVO))

    bloqueios: list[Periodo] = []
    for inicio_reserva, fim_reserva in db.execute(query.order_by(agenda.data_inicio)):
        inicio_bloqueio = max(inicio_reserva, inicio)
        fim_bloqueio = min(fim_reserva, fim)
        if bloqueios and inicio_bloqueio <= bloqueios[-1].data_fim:
            bloqueios[-1].data_fim = max(bloqueios[-1].data_fim, fim_bloqueio)
        else:
            bloqueios.append(Periodo(data_inicio=inicio_bloqueio, data_fim=fim_bloqueio))
    return bloqueios


def _janelas_livres(
    data: date,
    turnos: tuple[tuple[time, time], ...],
    bloqueios: list[Periodo],
) -> list[Periodo]:
    livres = []
    for abertura, fechamento in turnos:
        inicio = datetime.combine(data, abertura)
        fim = datetime.combine(data, fechamento)
        for bloqueio in bloqueios:
            if bloqueio.data_fim <= inicio:
                continue
            if bloqueio.data_inicio >= fim:
                break
            if inicio < bloqueio.data_inicio:
                livres.append(Periodo(data_inicio=inicio, data_fim=bloqueio.data_inicio))
            inicio = bloqueio.data_fim
        if inicio < fim:
            livres.append(Periodo(data_inicio=inicio, data_fim=fim))
    return livres


def _reservaveis(data: date, turnos, bloqueios: list[Periodo], minimo: timedelta) -> list[Periodo]:
    agora = horario_service.agora_local()
    primeiro_minuto = agora.replace(second=0, microsecond=0) + timedelta(minutes=1)
    periodos = []
    for janela in _janelas_livres(data, turnos, bloqueios):
        inicio = max(janela.data_inicio, primeiro_minuto)
        if janela.data_fim - inicio >= minimo:
            periodos.append(Periodo(data_inicio=inicio, data_fim=janela.data_fim))
    return periodos


def consultar_espaco(db: Session, data: date, espaco_id: int) -> DisponibilidadeEspacoResponse:
    bloqueios = _bloqueios_do_dia(db, data, espaco_id)
    return DisponibilidadeEspacoResponse(
        data=data,
        espaco_id=espaco_id,
        duracao_minima_horas=DURACAO_MINIMA_HORAS,
        duracao_maxima_horas=DURACAO_MAXIMA_HORAS,
        bloqueios=bloqueios,
        horarios_reservaveis=_reservaveis(data, _turnos_espaco(espaco_id), bloqueios, DURACAO_MINIMA_EVENTO),
    )


def consultar_visitas(db: Session, data: date) -> DisponibilidadeVisitaResponse:
    bloqueios = _bloqueios_do_dia(db, data, espaco_id=None)
    return DisponibilidadeVisitaResponse(
        data=data,
        bloqueios=bloqueios,
        horarios_reservaveis=_reservaveis(data, TURNOS_DIURNOS, bloqueios, DURACAO_VISITA),
    )
