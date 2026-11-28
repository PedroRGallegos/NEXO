"""Capa de servicios: varias conversaciones a la vez (lo que necesita una web).

El ``Agente`` maneja una sola conversación. El gestor crea un agente por conversación,
los reutiliza mientras el proceso vive, los recupera de disco cuando hace falta y
serializa el acceso a cada uno (un agente no es seguro entre hilos).
"""

import threading
from collections.abc import Callable
from contextlib import contextmanager

from dominio.excepciones import ErrorPersistencia, ModeloNoDisponible
from dominio.mensaje import Conversacion
from dominio.modelos import Modelo
from persistencia.repositorio_conversaciones import RepositorioConversaciones
from servicios.agente import Agente

TITULO_MAX = 40
_NOMBRES_NO_DISPONIBLES = {"llm": "ModeloLLM"}  # nombre público de los remotos aún sin instanciar


class GestorConversaciones:
    """Crea, recupera y guarda conversaciones; cada una con su propio ``Agente``."""

    def __init__(
        self,
        fabrica_agente: Callable[[], Agente],
        repositorio: RepositorioConversaciones,
        modelos: dict[str, Modelo],
        modelos_no_disponibles: dict[str, str] | None = None,
    ):
        self._fabrica = fabrica_agente
        self._repositorio = repositorio
        self._modelos = modelos
        # id -> motivo de los modelos remotos que existen pero no se pueden usar (p. ej. sin clave)
        self._no_disponibles = {k: v for k, v in (modelos_no_disponibles or {}).items() if k not in modelos}
        self._referencia = fabrica_agente()  # solo para consultar herramientas y registro de uso
        self._agentes: dict[str, Agente] = {}
        self._cerrojos: dict[str, threading.Lock] = {}
        self._cerrojo_general = threading.Lock()

    # --- Modelos ---------------------------------------------------------------
    @property
    def modelos(self) -> dict[str, Modelo]:
        return dict(self._modelos)

    def catalogo_modelos(self) -> list[dict]:
        """Todos los modelos conocidos (también los no disponibles), locales primero y remotos después."""
        locales, remotos = [], []
        for clave, modelo in self._modelos.items():
            entrada = {
                "id": clave,
                "nombre": type(modelo).__name__,
                "tipo": "remoto" if modelo.remoto else "local",
                "disponible": True,
                "motivo": None,
                "detalle": modelo.nombre if modelo.remoto else None,
            }
            (remotos if modelo.remoto else locales).append(entrada)
        for clave, motivo in self._no_disponibles.items():
            remotos.append(
                {"id": clave, "nombre": _NOMBRES_NO_DISPONIBLES.get(clave, clave), "tipo": "remoto",
                 "disponible": False, "motivo": motivo, "detalle": None}
            )
        return locales + remotos

    def id_modelo(self, agente: Agente) -> str:
        """Clave con la que se registró el modelo activo del agente."""
        return next((clave for clave, m in self._modelos.items() if m is agente.modelo), agente.nombre_modelo)

    def cambiar_modelo(self, agente: Agente, clave: str) -> None:
        modelo = self._modelos.get(clave)
        if modelo is None and clave in self._no_disponibles:
            raise ModeloNoDisponible(f"Modelo '{clave}' no disponible. {self._no_disponibles[clave]}")
        if modelo is None:
            raise ModeloNoDisponible(f"Modelo '{clave}' no disponible. Opciones: {', '.join(self._modelos)}.")
        agente.cambiar_modelo(modelo)

    def esquemas_herramientas(self) -> list[dict]:
        return self._referencia.esquemas_herramientas()

    def resumen_uso(self) -> dict:
        return self._referencia.resumen_uso()

    def resumen_uso_llm(self) -> dict:
        return self._referencia.resumen_uso_llm()

    # --- Ciclo de vida -----------------------------------------------------------
    def crear(self) -> Agente:
        agente = self._fabrica()
        with self._cerrojo_general:
            self._agentes[agente.conversacion.id] = agente
        return agente

    def obtener(self, id_conv: str) -> Agente:
        """Agente de la conversación ``id_conv`` (de memoria o cargada de disco)."""
        with self._cerrojo_general:
            agente = self._agentes.get(id_conv)
            if agente is not None:
                return agente
        conversacion = self._repositorio.cargar(id_conv)  # lanza ConversacionNoEncontrada
        agente = self._fabrica()
        agente.cargar_conversacion(conversacion)
        with self._cerrojo_general:
            return self._agentes.setdefault(id_conv, agente)

    @contextmanager
    def acceso_exclusivo(self, id_conv: str):
        """Bloquea la conversación mientras se procesa un mensaje."""
        with self._cerrojo_general:
            cerrojo = self._cerrojos.setdefault(id_conv, threading.Lock())
        with cerrojo:
            yield

    def guardar(self, agente: Agente) -> None:
        self._repositorio.guardar(agente.conversacion)

    # --- Consultas ---------------------------------------------------------------
    def listar(self) -> list[dict]:
        """Resumen de las conversaciones guardadas, la más reciente primero."""
        resumenes = []
        for id_conv in self._repositorio.listar():
            try:
                conversacion = self._repositorio.cargar(id_conv)
            except ErrorPersistencia:  # incluye ficheros dañados: se omiten
                continue
            resumenes.append(resumir(conversacion))
        return sorted(resumenes, key=lambda r: r["actualizada"], reverse=True)

    def todas_guardadas(self) -> list[Conversacion]:
        """Conversaciones guardadas en disco (para las estadísticas)."""
        conversaciones = []
        for id_conv in self._repositorio.listar():
            try:
                conversaciones.append(self._repositorio.cargar(id_conv))
            except ErrorPersistencia:  # incluye ficheros dañados: se omiten
                continue
        return conversaciones


def resumir(conversacion: Conversacion) -> dict:
    """``{id, titulo, mensajes, actualizada}`` de una conversación."""
    mensajes = conversacion.get_mensajes()
    primero = next((m.contenido for m in mensajes if m.rol == "usuario"), "Conversación vacía")
    titulo = primero if len(primero) <= TITULO_MAX else primero[: TITULO_MAX - 1].rstrip() + "…"
    return {
        "id": conversacion.id,
        "titulo": titulo,
        "mensajes": len(mensajes),
        "actualizada": str(mensajes[-1].fecha) if mensajes else "",
    }
