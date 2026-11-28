"""Sorpresas del chat: respuestas fijas a ciertos mensajes.

La animación de cada sorpresa vive en el frontend (``frontend/src/huevos.ts``). Aquí está lo que
NEXO contesta en el chat, para que no responda «No estoy seguro» mientras se ve la animación. Los
criterios de detección son los mismos que en ``huevos.ts``.
"""

import re

from dominio.texto import normalizar

# Marca que el frontend convierte en una imagen. Solo admite rutas de /sorpresas/ (ver ``imagenes.ts``).
IMAGEN_ALONSO = "[[imagen:/sorpresas/fernando-alonso.jpg]]"

_FRASE_ALONSO = re.compile(r"(?:^| )fernando alonso(?: |$)")


def _simplificar(texto: str) -> str:
    """Igual que ``normalizar`` de ``huevos.ts``: minúsculas, sin tildes y signos convertidos en espacios."""
    return re.sub(r"[^a-z0-9]+", " ", normalizar(texto)).strip()


def respuesta_sorpresa(texto: str) -> str | None:
    """Respuesta de la sorpresa que activa ``texto``, o ``None`` si no activa ninguna."""
    simple = _simplificar(texto)
    if _FRASE_ALONSO.search(simple):
        return IMAGEN_ALONSO
    return None
