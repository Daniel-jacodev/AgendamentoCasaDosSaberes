from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class ArquivoPDFBase(BaseModel):
    nome_original: str = Field(min_length=1, max_length=255)
    tamanho_bytes: int = Field(gt=0)
    content_type: str = "application/pdf"

class ArquivoPDFResponse(ArquivoPDFBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    criado_em: datetime