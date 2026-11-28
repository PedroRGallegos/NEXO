"""Herramientas que el agente puede ejecutar.

Todas heredan de ``Herramienta`` y sobrescriben ``ejecutar()``. El agente las
usa por polimorfismo: nunca necesita saber cuál es cuál.
"""

import copy
import math
import operator
from datetime import datetime
from typing import Callable

from dominio.excepciones import ArgumentosInvalidos
from dominio.texto import palabras

NO_ENCONTRADO = "No encontrado"


def _a_numero(valor, nombre: str) -> float:
    """Convierte ``valor`` en un número finito o lanza ``ArgumentosInvalidos``."""
    if isinstance(valor, bool):
        raise ArgumentosInvalidos(f"El argumento '{nombre}' debe ser un número, no {valor!r}.")
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ArgumentosInvalidos(
            f"El argumento '{nombre}' debe ser un número, no {valor!r}."
        ) from None
    if not math.isfinite(numero):
        raise ArgumentosInvalidos(f"El argumento '{nombre}' no es un número válido.")
    return numero


def _formatear_numero(numero: float) -> str:
    """Formato legible: 12.0 -> '12'; 239.70000000000002 -> '239.7'."""
    numero = round(numero, 10)
    if numero == int(numero):
        return str(int(numero))
    return f"{numero:.10f}".rstrip("0").rstrip(".")


def _mejor_coincidencia(texto: str, catalogo: dict):
    """Clave del catálogo que más palabras comparte con ``texto`` (``None`` si ninguna).

    Las claves del catálogo son cadenas de palabras normalizadas separadas por espacios.
    """
    palabras_texto = set(palabras(texto))
    mejor_clave, mejor_puntuacion = None, 0
    for clave in catalogo:
        puntuacion = len(palabras_texto & set(clave.split()))
        if puntuacion > mejor_puntuacion:
            mejor_clave, mejor_puntuacion = clave, puntuacion
    return mejor_clave


class Herramienta:
    """Clase base de todas las herramientas que puede usar el agente.

    ``parametros`` describe los argumentos de ``ejecutar()`` como propiedades de JSON Schema;
    con ellos ``esquema()`` produce el formato que piden las APIs de *tool calling*.
    """

    def __init__(self, nombre, descripcion, parametros=None, requeridos=None):
        self.nombre = nombre
        self.descripcion = descripcion
        self._parametros = dict(parametros or {})
        self._requeridos = list(self._parametros if requeridos is None else requeridos)

    def ejecutar(self, **kwargs) -> str:
        raise NotImplementedError("Cada herramienta debe implementar ejecutar()")

    def esquema(self) -> dict:
        """Descripción de la herramienta en formato JSON Schema (tool calling / MCP)."""
        return {
            "name": self.nombre,
            "description": self.descripcion,
            "input_schema": {
                "type": "object",
                "properties": copy.deepcopy(self._parametros),
                "required": list(self._requeridos),
            },
        }

    def __str__(self):
        return f"🔧 {self.nombre}: {self.descripcion}"


class Calculadora(Herramienta):
    """Operaciones aritméticas básicas entre dos números."""

    OPERACIONES = {
        "+": operator.add,
        "-": operator.sub,
        "*": operator.mul,
        "/": operator.truediv,
    }

    def __init__(self):
        super().__init__(
            "calculadora",
            "Suma, resta, multiplica o divide dos números (+ - * /).",
            parametros={
                "a": {"type": "number", "description": "Primer operando."},
                "b": {"type": "number", "description": "Segundo operando."},
                "operacion": {"type": "string", "enum": list(self.OPERACIONES), "description": "Operación."},
            },
        )

    def ejecutar(self, a=None, b=None, operacion=None, **_) -> str:
        if a is None or b is None or operacion is None:
            raise ArgumentosInvalidos("Faltan argumentos: se necesitan 'a', 'b' y 'operacion'.")
        if operacion not in self.OPERACIONES:
            raise ArgumentosInvalidos(
                f"Operación '{operacion}' no soportada. Usa una de: {' '.join(self.OPERACIONES)}"
            )
        x = _a_numero(a, "a")
        y = _a_numero(b, "b")
        if operacion == "/" and y == 0:
            raise ArgumentosInvalidos("No se puede dividir entre 0.")
        resultado = self.OPERACIONES[operacion](x, y)
        if not math.isfinite(resultado):
            raise ArgumentosInvalidos("El resultado es demasiado grande.")
        return f"{_formatear_numero(x)} {operacion} {_formatear_numero(y)} = {_formatear_numero(resultado)}"


class ConversorMoneda(Herramienta):
    """Convierte una cantidad entre EUR, USD, GBP y JPY."""

    TASAS_A_EUR = {"EUR": 1.0, "USD": 0.92, "GBP": 1.17, "JPY": 0.0062}

    def __init__(self):
        monedas = sorted(self.TASAS_A_EUR)
        super().__init__(
            "conversor_moneda",
            "Convierte una cantidad entre EUR, USD, GBP y JPY.",
            parametros={
                "cantidad": {"type": "number", "minimum": 0, "description": "Importe a convertir."},
                "origen": {"type": "string", "enum": monedas, "description": "Moneda de origen."},
                "destino": {"type": "string", "enum": monedas, "description": "Moneda de destino."},
            },
        )

    def _validar_moneda(self, codigo, nombre: str) -> str:
        if not isinstance(codigo, str) or codigo.strip().upper() not in self.TASAS_A_EUR:
            disponibles = ", ".join(sorted(self.TASAS_A_EUR))
            raise ArgumentosInvalidos(
                f"Moneda desconocida en '{nombre}': {codigo!r}. Disponibles: {disponibles}."
            )
        return codigo.strip().upper()

    def ejecutar(self, cantidad=None, origen=None, destino=None, **_) -> str:
        if cantidad is None or origen is None or destino is None:
            raise ArgumentosInvalidos("Faltan argumentos: se necesitan 'cantidad', 'origen' y 'destino'.")
        importe = _a_numero(cantidad, "cantidad")
        if importe < 0:
            raise ArgumentosInvalidos("La cantidad no puede ser negativa.")
        origen = self._validar_moneda(origen, "origen")
        destino = self._validar_moneda(destino, "destino")
        en_euros = importe * self.TASAS_A_EUR[origen]
        convertido = en_euros / self.TASAS_A_EUR[destino]
        return f"{_formatear_numero(importe)} {origen} = {convertido:.2f} {destino}"


class BuscadorFAQ(Herramienta):
    """Devuelve la respuesta de la FAQ que más palabras comparte con la pregunta (un RAG en miniatura)."""

    FAQ = {
        "envio plazo dias tarda": "Los envíos tardan 24-48 h en península y 3-5 días en islas.",
        "devolucion devolver garantia": "Tienes 30 días para devolver el producto sin dar explicaciones.",
        "horario atencion abierto": "Atendemos de lunes a viernes de 9:00 a 18:00.",
        "pago tarjeta bizum paypal": "Aceptamos tarjeta, Bizum y PayPal.",
    }

    def __init__(self):
        super().__init__(
            "buscador_faq",
            "Busca la respuesta a una pregunta frecuente de TechNova.",
            parametros={"pregunta": {"type": "string", "description": "Pregunta del cliente."}},
        )

    def ejecutar(self, pregunta=None, **_) -> str:
        if not isinstance(pregunta, str) or not pregunta.strip():
            raise ArgumentosInvalidos("Falta el argumento 'pregunta' (texto no vacío).")
        clave = _mejor_coincidencia(pregunta, self.FAQ)
        return NO_ENCONTRADO if clave is None else self.FAQ[clave]


class ConsultaStock(Herramienta):
    """Consulta las unidades disponibles de un producto del catálogo."""

    # clave de búsqueda (palabras normalizadas) -> (nombre para mostrar, unidades)
    STOCK = {
        "ssd 1tb": ("SSD 1 TB", 14),
        "ram ddr5 16gb": ("RAM DDR5 16 GB", 0),
        "tarjeta grafica rtx 4060": ("Tarjeta gráfica RTX 4060", 3),
        "monitor 27 pulgadas": ("Monitor 27 pulgadas", 7),
        "teclado mecanico": ("Teclado mecánico", 25),
    }

    def __init__(self):
        super().__init__(
            "consulta_stock",
            "Consulta las unidades en stock de un producto.",
            parametros={"producto": {"type": "string", "description": "Nombre del producto."}},
        )

    def ejecutar(self, producto=None, **_) -> str:
        if not isinstance(producto, str) or not producto.strip():
            raise ArgumentosInvalidos("Falta el argumento 'producto' (texto no vacío).")
        clave = _mejor_coincidencia(producto, self.STOCK)
        if clave is None:
            return NO_ENCONTRADO
        nombre, unidades = self.STOCK[clave]
        if unidades == 0:
            return f"{nombre}: agotado."
        return f"{nombre}: {unidades} {'unidad' if unidades == 1 else 'unidades'} en stock."


class Reloj(Herramienta):
    """Devuelve la fecha y la hora actuales (el reloj es inyectable para poder probarlo)."""

    DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
    MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre")

    def __init__(self, reloj: Callable[[], datetime] = datetime.now):
        super().__init__("reloj", "Dice la fecha y la hora actuales.")
        self._reloj = reloj

    def ejecutar(self, **_) -> str:
        ahora = self._reloj()
        return (
            f"Hoy es {self.DIAS[ahora.weekday()]} {ahora.day} de {self.MESES[ahora.month - 1]} "
            f"de {ahora.year} y son las {ahora:%H:%M}."
        )
