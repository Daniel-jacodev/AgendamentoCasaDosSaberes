from datetime import datetime

from app.constants.horarios import (
  INICIO_EXPEDIENTE,
  FIM_EXPEDIENTE,
  INICIO_INTERVALO,
  FIM_INTERVALO,
  DURACAO_MINIMA_HORAS,
  DURACAO_MAXIMA_HORAS,
)

def horario_valido(inicio: datetime, fim: datetime) -> bool:
    duracao_horas = (fim - inicio).total_seconds() / 3600
    
    if not DURACAO_MINIMA_HORAS <= duracao_horas <= DURACAO_MAXIMA_HORAS:
      return False
    
    inicio_hora = inicio.time()
    fim_hora = fim.time()
    
    if inicio_hora < INICIO_EXPEDIENTE or fim_hora > FIM_EXPEDIENTE:
      return False
    
    conflito_intervalo = (
      inicio_hora < FIM_INTERVALO and fim_hora > INICIO_INTERVALO
    )
    
    if conflito_intervalo:
      return False
    
    return True
  
def horario_evento_valido(
    inicio: datetime,
    fim: datetime,
    administrador: bool = False,
) -> bool:
    if administrador and inicio.time() >= FIM_EXPEDIENTE:
        duracao_horas = (fim - inicio).total_seconds() / 3600

        return DURACAO_MINIMA_HORAS <= duracao_horas <= DURACAO_MAXIMA_HORAS

    return horario_valido(inicio, fim)