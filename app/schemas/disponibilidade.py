from datetime import date, datetime

from pydantic import BaseModel


class Periodo(BaseModel):
    data_inicio: datetime
    data_fim: datetime


class DisponibilidadeVisitaResponse(BaseModel):
    data: date
    horarios_reservaveis: list[Periodo]
    bloqueios: list[Periodo]


class DisponibilidadeEspacoResponse(DisponibilidadeVisitaResponse):
    espaco_id: int
    duracao_minima_horas: int
    duracao_maxima_horas: int
