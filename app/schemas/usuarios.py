from pydantic import BaseModel, EmailStr, Field, SecretStr


class UsuarioCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255, pattern=r'\S')
    email: EmailStr
    senha: SecretStr = Field(min_length=8, max_length=128)


class UsuarioResponse(BaseModel):
    id: str
    email: EmailStr
    nome: str


class LoginRequest(BaseModel):
    email: EmailStr
    senha: SecretStr = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    refresh_expires_in: int
    token_type: str
