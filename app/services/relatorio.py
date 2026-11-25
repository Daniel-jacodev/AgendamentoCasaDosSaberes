from bisect import insort
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evento import Evento
from app.models.visita import NaturezaInstituicaoEnum, StatusVisitaEnum, Visita
from app.schemas.relatorio import FiltroRelatorio

LIMITE_RANKING = 5
NATUREZAS = {
    NaturezaInstituicaoEnum.PUBLICA: 'Pública',
    NaturezaInstituicaoEnum.PRIVADA: 'Privada',
    NaturezaInstituicaoEnum.OUTRA: 'Outra',
    None: 'Não informada',
}


@dataclass
class ResumoAgenda:
    confirmados: int = 0
    pendentes: int = 0
    negados: int = 0
    cancelados: int = 0
    dias: Counter[int] = field(default_factory=Counter)
    horarios: Counter[int] = field(default_factory=Counter)

    def contabilizar(self, inicio: datetime, status: str) -> None:
        if status == 'aceito':
            self.confirmados += 1
            self.dias[inicio.weekday()] += 1
            self.horarios[inicio.hour] += 1
        elif status == 'pendente':
            self.pendentes += 1
        elif status == 'negado':
            self.negados += 1
        elif status == 'cancelado':
            self.cancelados += 1


@dataclass
class EventoRankeado:
    titulo: str
    inicio: datetime
    publico_estimado: int

    def ordem(self) -> tuple[int, datetime, str]:
        return -self.publico_estimado, self.inicio, self.titulo


@dataclass
class ResumoEventos(ResumoAgenda):
    pautas: Counter[str] = field(default_factory=Counter)
    publico_estimado: int = 0
    eventos_com_estimativa: int = 0
    ranking: list[EventoRankeado] = field(default_factory=list)


@dataclass
class ResumoVisitas(ResumoAgenda):
    instituicoes: Counter[str] = field(default_factory=Counter)
    pessoas_previstas: int = 0
    grupos_com_pcd: int = 0


def resumir_eventos(db: Session, inicio: datetime, fim: datetime, status: str = 'todos') -> ResumoEventos:
    resumo = ResumoEventos()
    dados = select(
        Evento.titulo, Evento.data_inicio, Evento.status, Evento.pauta, Evento.pautas, Evento.publico_estimado
    )
    dados = dados.where(Evento.data_inicio.between(inicio, fim))
    if status != 'todos':
        dados = dados.where(Evento.status == status)
    for titulo, data_inicio, estado, pauta, pautas, publico in db.execute(dados):
        resumo.contabilizar(data_inicio, estado)
        if estado == 'aceito':
            resumo.pautas.update(pautas or [pauta.value if pauta is not None else 'Não informada'])
            if publico is not None:
                resumo.eventos_com_estimativa += 1
                resumo.publico_estimado += publico
                insort(resumo.ranking, EventoRankeado(titulo, data_inicio, publico), key=EventoRankeado.ordem)
                if len(resumo.ranking) > LIMITE_RANKING:
                    resumo.ranking.pop()
    return resumo


def resumir_visitas(db: Session, inicio: datetime, fim: datetime, status: str = 'todos') -> ResumoVisitas:
    resumo = ResumoVisitas()
    dados = select(
        Visita.data_inicio, Visita.status, Visita.natureza_instituicao, Visita.quantidade_pessoas, Visita.possui_pcd
    ).where(Visita.data_inicio.between(inicio, fim))
    estados = {
        'aceito': StatusVisitaEnum.APROVADA.value,
        'pendente': StatusVisitaEnum.PENDENTE.value,
        'negado': StatusVisitaEnum.NEGADA.value,
        'cancelado': StatusVisitaEnum.CANCELADA.value,
    }
    if status != 'todos':
        dados = dados.where(Visita.status == estados[status])
    rotulos = {valor: chave for chave, valor in estados.items()}
    for data_inicio, estado, natureza, pessoas, possui_pcd in db.execute(dados):
        resumo.contabilizar(data_inicio, rotulos[estado])
        if estado == StatusVisitaEnum.APROVADA.value:
            resumo.instituicoes[NATUREZAS[natureza]] += 1
            resumo.pessoas_previstas += pessoas
            resumo.grupos_com_pcd += int(possui_pcd)
    return resumo


def consultar_relatorio(db: Session, filtro: FiltroRelatorio) -> tuple[ResumoEventos | None, ResumoVisitas | None]:
    inicio = datetime.combine(filtro.data_inicio, time.min)
    fim = datetime.combine(filtro.data_fim, time.max)
    eventos = resumir_eventos(db, inicio, fim, filtro.status) if filtro.tipo != 'visitas' else None
    visitas = resumir_visitas(db, inicio, fim, filtro.status) if filtro.tipo != 'eventos' else None
    return eventos, visitas
