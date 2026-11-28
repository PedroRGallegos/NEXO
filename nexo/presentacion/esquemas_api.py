"""Contratos de la API web (validación de entrada con Pydantic)."""

from pydantic import BaseModel, ConfigDict, Field

MAX_CARACTERES_MENSAJE = 2000


class PeticionMensaje(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    texto: str = Field(min_length=1, max_length=MAX_CARACTERES_MENSAJE)


class PeticionModelo(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    modelo: str = Field(min_length=1, max_length=40)
