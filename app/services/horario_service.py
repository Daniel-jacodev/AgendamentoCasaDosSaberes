from datetime import datetime
from zoneinfo import ZoneInfo

FUSO_DA_CASA = ZoneInfo('America/Fortaleza')


def horario_local(valor: datetime) -> datetime:
    if valor.tzinfo is None:
        return valor
    return valor.astimezone(FUSO_DA_CASA).replace(tzinfo=None)


def agora_local() -> datetime:
    return datetime.now(FUSO_DA_CASA).replace(tzinfo=None)
