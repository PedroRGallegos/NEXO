"""Utilidades de texto compartidas por herramientas y modelos."""

import re
import unicodedata


def normalizar(texto: str) -> str:
    """Devuelve el texto en minúsculas y sin tildes ni diéresis.

    >>> normalizar("¿Cuánto tarda el ENVÍO?")
    '¿cuanto tarda el envio?'
    """
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def palabras(texto: str) -> list[str]:
    """Lista de palabras (normalizadas) de un texto, sin signos de puntuación."""
    return re.findall(r"\w+", normalizar(texto))
