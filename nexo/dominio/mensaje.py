"""Mensaje y Conversacion: la memoria a corto plazo del agente."""

import re
import uuid
from datetime import datetime

from dominio.excepciones import LimiteContextoSuperado

ROLES_VALIDOS = ("usuario", "asistente", "herramienta")

# Convención para los mensajes de rol "herramienta": "[nombre] resultado".
# Así el modelo sabe qué herramienta produjo el resultado.
PREFIJO_ERROR = "Error: "
PREFIJO_RESUMEN = "[resumen] "
_PATRON_HERRAMIENTA = re.compile(r"^\[(?P<nombre>[^\]]+)\]\s*(?P<resto>.*)$", re.DOTALL)


class Mensaje:
    """Un mensaje de la conversación. Es inmutable de cara al exterior."""

    def __init__(self, rol: str, contenido: str, fecha: str | None = None):
        if rol not in ROLES_VALIDOS:
            raise ValueError(
                f"Rol '{rol}' no válido. Roles permitidos: {', '.join(ROLES_VALIDOS)}"
            )
        if not isinstance(contenido, str):
            raise TypeError("El contenido de un mensaje debe ser texto.")
        self._rol = rol
        self._contenido = contenido
        self._fecha = fecha or datetime.now().isoformat()

    # --- Solo lectura -----------------------------------------------------
    @property
    def rol(self) -> str:
        return self._rol

    @property
    def contenido(self) -> str:
        return self._contenido

    @property
    def fecha(self) -> str:
        return self._fecha

    # --- Constructores alternativos ---------------------------------------
    @classmethod
    def de_herramienta(cls, nombre: str, resultado: str, error: bool = False) -> "Mensaje":
        """Crea un mensaje de rol ``herramienta`` con el formato ``[nombre] resultado``."""
        prefijo = PREFIJO_ERROR if error else ""
        return cls("herramienta", f"[{nombre}] {prefijo}{resultado}")

    @classmethod
    def from_dict(cls, datos: dict) -> "Mensaje":
        """Reconstruye un mensaje a partir del diccionario de ``to_dict()``."""
        return cls(datos["rol"], datos["contenido"], datos.get("fecha"))

    # --- Utilidades -------------------------------------------------------
    def desglosar_herramienta(self) -> tuple[str, str, bool]:
        """Devuelve ``(nombre_herramienta, texto, es_error)`` de un mensaje de herramienta.

        Lanza ``ValueError`` si el mensaje no es de rol herramienta o no sigue el formato.
        """
        if self._rol != "herramienta":
            raise ValueError("Solo los mensajes de rol 'herramienta' se pueden desglosar.")
        coincidencia = _PATRON_HERRAMIENTA.match(self._contenido)
        if coincidencia is None:
            raise ValueError("El mensaje de herramienta no tiene el formato '[nombre] resultado'.")
        resto = coincidencia.group("resto")
        es_error = resto.startswith(PREFIJO_ERROR)
        texto = resto[len(PREFIJO_ERROR):] if es_error else resto
        return coincidencia.group("nombre"), texto, es_error

    def to_dict(self) -> dict:
        return {"rol": self._rol, "contenido": self._contenido, "fecha": self._fecha}

    def __str__(self) -> str:
        return f"[{self._rol}] {self._contenido}"

    def __repr__(self) -> str:
        return f"Mensaje(rol={self._rol!r}, contenido={self._contenido!r})"


class Conversacion:
    """Historial de mensajes con un límite de tokens (versión de juguete de una ventana de contexto)."""

    LIMITE_TOKENS_POR_DEFECTO = 500
    TOKENS_POR_PALABRA = 1.3

    def __init__(self, id_conv: str | None = None, limite_tokens: int = LIMITE_TOKENS_POR_DEFECTO):
        if limite_tokens <= 0:
            raise ValueError("El límite de tokens debe ser positivo.")
        self.id = id_conv or uuid.uuid4().hex[:8]
        self.__mensajes: list[Mensaje] = []  # privado: solo se toca mediante métodos
        self.__palabras = 0  # contador incremental: evita recorrer todo el historial en cada mensaje
        self._limite_tokens = limite_tokens  # protegido

    @property
    def limite_tokens(self) -> int:
        """Límite de tokens (solo lectura)."""
        return self._limite_tokens

    @classmethod
    def _tokens_de(cls, palabras: int) -> int:
        """Número total de palabras × 1,3, redondeado."""
        return round(palabras * cls.TOKENS_POR_PALABRA)

    @staticmethod
    def _contar_palabras(mensajes: list[Mensaje]) -> int:
        return sum(len(m.contenido.split()) for m in mensajes)

    def agregar(self, mensaje: Mensaje) -> None:
        """Añade un mensaje. Si con él se supera el límite, lanza ``LimiteContextoSuperado``
        y el mensaje NO se añade."""
        if not isinstance(mensaje, Mensaje):
            raise TypeError("Solo se pueden agregar objetos Mensaje.")
        palabras = self.__palabras + len(mensaje.contenido.split())
        tokens_con_mensaje = self._tokens_de(palabras)
        if tokens_con_mensaje > self._limite_tokens:
            raise LimiteContextoSuperado(
                f"La conversación superaría el límite de {self._limite_tokens} tokens "
                f"({tokens_con_mensaje} estimados)."
            )
        self.__mensajes.append(mensaje)
        self.__palabras = palabras

    def compactar(self, resumen: str, conservar_desde: int) -> None:
        """Sustituye los mensajes anteriores a la posición ``conservar_desde`` por un único
        mensaje-resumen. Así gestionan la memoria los agentes reales."""
        if not 0 < conservar_desde <= len(self.__mensajes):
            raise ValueError("Posición de compactación fuera de rango.")
        mensaje_resumen = Mensaje("asistente", f"{PREFIJO_RESUMEN}{resumen}")
        self.__mensajes = [mensaje_resumen] + self.__mensajes[conservar_desde:]
        self.__palabras = self._contar_palabras(self.__mensajes)

    def get_mensajes(self) -> list[Mensaje]:
        """Copia de la lista: quien la reciba no puede alterar el historial real."""
        return list(self.__mensajes)

    def tokens_estimados(self) -> int:
        return self._tokens_de(self.__palabras)

    def __len__(self) -> int:
        return len(self.__mensajes)

    def to_dict(self) -> dict:
        return {"id": self.id, "mensajes": [m.to_dict() for m in self.__mensajes]}

    @classmethod
    def from_dict(cls, datos: dict) -> "Conversacion":
        """Reconstruye una conversación guardada.

        Los mensajes se restauran tal cual, sin volver a comprobar el límite:
        ya fueron aceptados cuando se guardó la conversación.
        """
        id_conv = datos["id"]
        if not isinstance(id_conv, str):
            raise TypeError("El id de la conversación debe ser texto.")
        conversacion = cls(id_conv=id_conv)
        conversacion.__mensajes = [Mensaje.from_dict(m) for m in datos["mensajes"]]
        conversacion.__palabras = cls._contar_palabras(conversacion.__mensajes)
        return conversacion
