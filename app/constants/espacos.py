from enum import Enum

ESPACO_SALAS_LEGADO_ID = 3
ESPACO_AREA_EXTERNA_ID = 5
ESPACO_SALA_1_ID = 6
ESPACO_SALA_2_ID = 7
ESPACO_CORREDOR_ID = 8

ESPACOS = {
    1: 'Auditório',
    2: 'Quintal',
    ESPACO_SALAS_LEGADO_ID: 'Salas Expositivas',
    4: 'Varanda',
    ESPACO_AREA_EXTERNA_ID: 'Área Externa',
    ESPACO_SALA_1_ID: 'Sala 1',
    ESPACO_SALA_2_ID: 'Sala 2',
    ESPACO_CORREDOR_ID: 'Corredor',
}
ESPACO_ID_MINIMO = min(ESPACOS)
ESPACO_ID_MAXIMO = max(ESPACOS)
DESCRICAO_ESPACOS = '; '.join(f'{id_espaco} = {nome}' for id_espaco, nome in ESPACOS.items())


def espacos_conflitantes(espaco_id: int) -> tuple[int, ...]:
    # As reservas antigas de Salas Expositivas não identificam uma sala individual.
    salas = (ESPACO_SALA_1_ID, ESPACO_SALA_2_ID)
    if espaco_id == ESPACO_SALAS_LEGADO_ID:
        return (espaco_id, *salas)
    if espaco_id in salas:
        return (espaco_id, ESPACO_SALAS_LEGADO_ID)
    return (espaco_id,)


class Espaco(str, Enum):
    AUDITORIO = 'auditorio'
    QUINTAL = 'quintal'
    VARANDA = 'varanda'
    AREA_EXTERNA = 'area_externa'
    SALAS_EXPOSITIVAS = 'salas_expositivas'
    SALA_1 = 'sala_1'
    SALA_2 = 'sala_2'
    CORREDOR = 'corredor'
