"""Persistencia de conversaciones: un fichero JSON por conversación."""

import json
import os
import re
from pathlib import Path

from dominio.excepciones import ConversacionNoEncontrada, ErrorPersistencia
from dominio.mensaje import Conversacion


class RepositorioConversaciones:
    """Guarda y carga conversaciones como ``{id}.json``."""

    _ID_VALIDO = re.compile(r"^[\w-]{1,64}$")  # evita rutas como "../secreto" y nombres de fichero imposibles

    def __init__(self, carpeta="datos/conversaciones"):
        self._carpeta = Path(carpeta)
        try:
            self._carpeta.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise ErrorPersistencia(f"No se puede crear la carpeta '{self._carpeta}': {error}") from error

    def _ruta(self, id_conv: str) -> Path:
        if not isinstance(id_conv, str) or not self._ID_VALIDO.match(id_conv):
            raise ConversacionNoEncontrada(f"Identificador de conversación no válido: {id_conv!r}")
        return self._carpeta / f"{id_conv}.json"

    def guardar(self, conversacion: Conversacion) -> None:
        ruta = self._ruta(conversacion.id)
        temporal = ruta.with_name(ruta.name + ".tmp")
        try:
            # Escritura atómica: si el programa se interrumpe, nunca queda un JSON a medias.
            with temporal.open("w", encoding="utf-8") as fichero:
                json.dump(conversacion.to_dict(), fichero, ensure_ascii=False, indent=2)
            os.replace(temporal, ruta)
        except OSError as error:
            temporal.unlink(missing_ok=True)
            raise ErrorPersistencia(f"No se pudo guardar la conversación: {error}") from error

    def cargar(self, id_conv: str) -> Conversacion:
        ruta = self._ruta(id_conv)
        try:
            with ruta.open("r", encoding="utf-8") as fichero:
                datos = json.load(fichero)
            return Conversacion.from_dict(datos)
        except FileNotFoundError:
            raise ConversacionNoEncontrada(f"No existe la conversación '{id_conv}'.") from None
        except OSError as error:
            raise ErrorPersistencia(f"No se pudo leer la conversación '{id_conv}': {error}") from error
        except (ValueError, KeyError, TypeError, AttributeError, RecursionError):
            # JSONDecodeError es subclase de ValueError; RecursionError: JSON anidado en exceso
            raise ErrorPersistencia(f"El fichero de la conversación '{id_conv}' está dañado.") from None

    def listar(self) -> list[str]:
        """Ids de las conversaciones guardadas, ordenados alfabéticamente."""
        return sorted(ruta.stem for ruta in self._carpeta.glob("*.json"))
