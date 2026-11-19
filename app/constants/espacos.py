from enum import Enum

ESPACO_AREA_EXTERNA_ID = 5


class Espaco(str, Enum):
    AUDITORIO = 'auditorio'
    QUINTAL = 'quintal'
    VARANDA = 'varanda'
    AREA_EXTERNA = 'area_externa'
    SALAS_EXPOSITIVAS = 'salas_expositivas'
