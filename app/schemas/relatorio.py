from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator


class FiltroRelatorio(BaseModel):
    tipo: Literal['eventos', 'visitas', 'ambos']
    status: Literal['todos', 'aceito', 'pendente', 'negado', 'cancelado'] = 'todos'
    data_inicio: date = Field(description='Primeiro dia do período, inclusive.')
    data_fim: date = Field(description='Último dia do período, inclusive.')

    @model_validator(mode='after')
    def validar_periodo(self) -> Self:
        if self.data_fim < self.data_inicio:
            raise ValueError('A data de fim deve ser igual ou posterior à data de início.')
        return self
