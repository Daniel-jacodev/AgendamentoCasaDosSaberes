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
    dias: Counter[int] = field(default_factory=Counter)
    horarios: Counter[int] = field(default_factory=Counter)

    def contabilizar(self, inicio: datetime, confirmado: bool) -> None:
        if confirmado:
            self.confirmados += 1
            self.dias[inicio.weekday()] += 1
            self.horarios[inicio.hour] += 1
        else:
            self.pendentes += 1


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


def resumir_eventos(db: Session, inicio: datetime, fim: datetime) -> ResumoEventos:
    resumo = ResumoEventos()
    dados = select(Evento.titulo, Evento.data_inicio, Evento.status, Evento.pauta, Evento.publico_estimado).where(
        Evento.data_inicio.between(inicio, fim)
    )
    for titulo, data_inicio, status, pauta, publico in db.execute(dados):
        confirmado = status == 'aceito'
        resumo.contabilizar(data_inicio, confirmado)
        if confirmado:
            resumo.pautas[pauta.value if pauta is not None else 'Não informada'] += 1
            if publico is not None:
                resumo.eventos_com_estimativa += 1
                resumo.publico_estimado += publico
                insort(resumo.ranking, EventoRankeado(titulo, data_inicio, publico), key=EventoRankeado.ordem)
                if len(resumo.ranking) > LIMITE_RANKING:
                    resumo.ranking.pop()
    return resumo


def resumir_visitas(db: Session, inicio: datetime, fim: datetime) -> ResumoVisitas:
    resumo = ResumoVisitas()
    dados = select(
        Visita.data_inicio, Visita.status, Visita.natureza_instituicao, Visita.quantidade_pessoas, Visita.possui_pcd
    ).where(Visita.data_inicio.between(inicio, fim))
    for data_inicio, status, natureza, pessoas, possui_pcd in db.execute(dados):
        confirmado = status == StatusVisitaEnum.APROVADA.value
        resumo.contabilizar(data_inicio, confirmado)
        if confirmado:
            resumo.instituicoes[NATUREZAS[natureza]] += 1
            resumo.pessoas_previstas += pessoas
            resumo.grupos_com_pcd += int(possui_pcd)
    return resumo


def consultar_relatorio(db: Session, filtro: FiltroRelatorio) -> tuple[ResumoEventos | None, ResumoVisitas | None]:
    inicio = datetime.combine(filtro.data_inicio, time.min)
    fim = datetime.combine(filtro.data_fim, time.max)
    eventos = resumir_eventos(db, inicio, fim) if filtro.tipo != 'visitas' else None
    visitas = resumir_visitas(db, inicio, fim) if filtro.tipo != 'eventos' else None
    return eventos, visitas
