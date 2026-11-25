from calendar import monthrange
from collections.abc import Iterator
from datetime import date, datetime, timedelta

from sqlalchemy import and_, or_

from app.models.evento import PERIODICIDADES_RECORRENTES, Evento, PeriodicidadeEnum

type Intervalo = tuple[datetime, datetime]

DIAS_POR_SEMANA = 7
MESES_POR_ANO = 12


def _datas_mensais(primeira: date, desde: date, ate: date) -> Iterator[date]:
    mes_inicial = primeira.year * MESES_POR_ANO + primeira.month - 1
    primeiro_mes = desde.year * MESES_POR_ANO + desde.month - 1
    ultimo_mes = ate.year * MESES_POR_ANO + ate.month - 1
    for indice in range(max(mes_inicial, primeiro_mes), ultimo_mes + 1):
        ano, mes_zero = divmod(indice, MESES_POR_ANO)
        mes = mes_zero + 1
        dia = min(primeira.day, monthrange(ano, mes)[1])
        yield date(ano, mes, dia)


def intervalos_evento(
    primeira_ocorrencia: Intervalo,
    periodicidade: PeriodicidadeEnum | None,
    limite: date | None,
    *,
    desde: date = date.min,
    ate: date = date.max,
) -> Iterator[Intervalo]:
    inicio, fim = primeira_ocorrencia
    if limite is None or periodicidade not in PERIODICIDADES_RECORRENTES:
        if inicio.date() <= ate and fim.date() >= desde:
            yield inicio, fim
        return

    primeira = inicio.date()
    desde = max(primeira, desde)
    ate = min(limite, ate)
    duracao = fim - inicio
    if periodicidade == PeriodicidadeEnum.SEMANAL:
        primeiro_dia = (desde - primeira).days
        deslocamento = primeiro_dia + (-primeiro_dia % DIAS_POR_SEMANA)
        datas = (
            primeira + timedelta(days=dias) for dias in range(deslocamento, (ate - primeira).days + 1, DIAS_POR_SEMANA)
        )
    else:
        datas = _datas_mensais(primeira, desde, ate)

    for dia in datas:
        if desde <= dia <= ate:
            comeco = datetime.combine(dia, inicio.time())
            yield comeco, comeco + duracao


def intervalos_programados(evento: Evento, *, desde: date = date.min, ate: date = date.max) -> Iterator[Intervalo]:
    limite = evento.data_fim_recorrencia if evento.status == 'aceito' else None
    return intervalos_evento((evento.data_inicio, evento.data_fim), evento.periodicidade, limite, desde=desde, ate=ate)


def eventos_no_periodo(inicio: datetime, fim: datetime):
    return (
        Evento.data_inicio <= fim,
        or_(
            Evento.data_fim >= inicio,
            and_(Evento.status == 'aceito', Evento.data_fim_recorrencia >= inicio.date()),
        ),
    )
