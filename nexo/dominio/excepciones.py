"""Excepciones propias de NEXO.

Todas heredan de ``ErrorAgente``, de modo que la capa de presentación puede
capturarlas con un único ``except ErrorAgente`` y mostrar un mensaje amable.
"""


class ErrorAgente(Exception):
    """Excepción base de NEXO."""


class HerramientaNoEncontrada(ErrorAgente):
    """El modelo ha pedido una herramienta que el agente no tiene registrada."""


class ArgumentosInvalidos(ErrorAgente):
    """Una herramienta ha recibido argumentos que no puede procesar."""


class LimiteContextoSuperado(ErrorAgente):
    """La conversación supera el límite de tokens permitido."""


class ErrorPersistencia(ErrorAgente):
    """Fallo al leer o escribir datos en disco (JSON o CSV)."""


class ConversacionNoEncontrada(ErrorPersistencia):
    """No existe la conversación solicitada en el repositorio."""


class ModeloNoDisponible(ErrorAgente):
    """Se ha pedido un modelo que no está registrado."""


class ErrorProveedorLLM(ErrorAgente):
    """El proveedor externo no pudo completar una petición al modelo."""
