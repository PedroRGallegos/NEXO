"""Capa de presentación: chat por terminal.

Solo lee lo que escribe la persona, llama al agente y muestra el resultado.
No toma decisiones de negocio.
"""

import json
import re
import unicodedata
from typing import Callable

from dominio.excepciones import ErrorAgente, LimiteContextoSuperado
from dominio.modelos import Modelo, ModeloEco, ModeloReglas
from persistencia.repositorio_conversaciones import RepositorioConversaciones
from servicios.agente import Agente

PROMPT_USUARIO = "tú > "
PROMPT_NEXO = "NEXO > "

AYUDA = """Comandos disponibles:
  /herramientas        Lista las herramientas
  /esquemas            Muestra las herramientas en JSON Schema
  /modelo eco|reglas   Cambia de modelo en caliente
  /historial           Muestra los mensajes y los tokens estimados
  /guardar             Guarda la conversación en disco
  /cargar <id>         Carga una conversación guardada
  /lista               Lista las conversaciones guardadas
  /nueva               Empieza una conversación nueva
  /limpiar             Guarda la conversación y empieza de cero (el historial se conserva)
  /stats               Resumen del uso de herramientas
  /ayuda               Muestra esta ayuda
  /salir               Termina el programa"""


def _ancho_visual(texto: str) -> int:
    """Ancho en columnas de terminal (los emojis ocupan 2)."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in texto)


def _caja(lineas: list[str], ancho: int = 38) -> str:
    cuerpo = [f"│{linea}{' ' * (ancho - _ancho_visual(linea))}│" for linea in lineas]
    return "\n".join([f"╭{'─' * ancho}╮", *cuerpo, f"╰{'─' * ancho}╯"])


class ChatConsola:
    """Interfaz de terminal para el agente."""

    def __init__(
        self,
        agente: Agente,
        repositorio: RepositorioConversaciones | None = None,
        modelos: dict[str, Modelo] | None = None,
        entrada: Callable[[str], str] = input,
        salida: Callable[[str], None] = print,
    ):
        self._agente = agente
        self._repositorio = repositorio
        self._modelos = modelos if modelos is not None else {"eco": ModeloEco(), "reglas": ModeloReglas()}
        self._entrada = entrada
        self._salida = salida
        self._activo = False
        self._comandos: dict[str, Callable[[str], None]] = {
            "/herramientas": self._cmd_herramientas,
            "/esquemas": self._cmd_esquemas,
            "/modelo": self._cmd_modelo,
            "/historial": self._cmd_historial,
            "/guardar": self._cmd_guardar,
            "/cargar": self._cmd_cargar,
            "/lista": self._cmd_lista,
            "/nueva": self._cmd_nueva,
            "/limpiar": self._cmd_limpiar,
            "/stats": self._cmd_stats,
            "/ayuda": self._cmd_ayuda,
            "/salir": self._cmd_salir,
        }

    # --- Bucle principal -------------------------------------------------------
    def iniciar(self) -> None:
        self._salida(_caja([" 🤖 NEXO · asistente de TechNova", " Escribe /herramientas o /salir"]))
        self._activo = True
        while self._activo:
            try:
                linea = self._entrada(PROMPT_USUARIO).strip()
            except (EOFError, KeyboardInterrupt):
                self._salida("")
                self._cmd_salir("")
                break
            if not linea:
                continue
            try:
                if linea.startswith("/"):
                    self._ejecutar_comando(linea)
                else:
                    self._responder(linea)
            except LimiteContextoSuperado as error:
                self._salida(f"⚠️  {error} Usa /nueva para empezar una conversación nueva.")
            except ErrorAgente as error:
                self._salida(f"⚠️  {error}")
            except Exception as error:  # red de seguridad: el chat nunca se cierra por un fallo
                self._salida(f"⚠️  Error inesperado ({type(error).__name__}): {error}")

    def _responder(self, texto: str) -> None:
        respuesta = self._agente.procesar(texto)
        for nombre, argumentos in self._agente.llamadas_realizadas:
            lista_args = ", ".join(f"{clave}={valor!r}" for clave, valor in argumentos.items())
            self._salida(f"🔧 {nombre}({lista_args})")
        respuesta = re.sub(r"\[\[imagen:([^\]]+)\]\]", r"(imagen: \1)", respuesta)  # la consola no muestra imágenes
        self._salida(f"{PROMPT_NEXO}{respuesta}")

    def _ejecutar_comando(self, linea: str) -> None:
        partes = linea.split(maxsplit=1)
        comando = partes[0].lower()
        argumento = partes[1].strip() if len(partes) > 1 else ""
        manejador = self._comandos.get(comando)
        if manejador is None:
            self._salida(f"Comando desconocido: {comando}. Escribe /ayuda para ver los disponibles.")
            return
        manejador(argumento)

    # --- Comandos Nivel 1 ------------------------------------------------------
    def _cmd_herramientas(self, _: str) -> None:
        for descripcion in self._agente.listar_herramientas():
            self._salida(descripcion)

    def _cmd_esquemas(self, _: str) -> None:
        self._salida(json.dumps(self._agente.esquemas_herramientas(), ensure_ascii=False, indent=2))

    def _cmd_modelo(self, argumento: str) -> None:
        disponibles = " · ".join(f"/modelo {clave}" for clave in self._modelos)
        elegido = self._modelos.get(argumento.lower())
        if elegido is None:
            self._salida(f"Modelo actual: {self._agente.nombre_modelo}. Opciones: {disponibles}")
            return
        self._agente.cambiar_modelo(elegido)
        self._salida(f"✔ Modelo cambiado a {self._agente.nombre_modelo}")

    def _cmd_ayuda(self, _: str) -> None:
        self._salida(AYUDA)

    def _cmd_salir(self, _: str) -> None:
        self._activo = False
        self._salida("👋 ¡Hasta pronto!")

    # --- Comandos Nivel 2 ------------------------------------------------------
    def _cmd_historial(self, _: str) -> None:
        conversacion = self._agente.conversacion
        mensajes = conversacion.get_mensajes()
        if not mensajes:
            self._salida("Todavía no hay mensajes en esta conversación.")
            return
        for mensaje in mensajes:
            self._salida(str(mensaje))
        self._salida(
            f"— {len(conversacion)} mensajes · "
            f"{conversacion.tokens_estimados()}/{conversacion.limite_tokens} tokens estimados"
        )

    def _repositorio_activo(self) -> RepositorioConversaciones | None:
        if self._repositorio is None:
            self._salida("La memoria en disco no está activada en esta sesión.")
        return self._repositorio

    def _cmd_guardar(self, _: str) -> None:
        repositorio = self._repositorio_activo()
        if repositorio is None:
            return
        repositorio.guardar(self._agente.conversacion)
        self._salida(f"💾 Conversación {self._agente.conversacion.id} guardada")

    def _cmd_cargar(self, argumento: str) -> None:
        repositorio = self._repositorio_activo()
        if repositorio is None:
            return
        if not argumento:
            self._salida("Uso: /cargar <id>. Mira los ids disponibles con /lista.")
            return
        conversacion = repositorio.cargar(argumento)
        self._agente.cargar_conversacion(conversacion)
        self._salida(f"📂 Conversación {conversacion.id} cargada ({len(conversacion)} mensajes)")

    def _cmd_lista(self, _: str) -> None:
        repositorio = self._repositorio_activo()
        if repositorio is None:
            return
        ids = repositorio.listar()
        if not ids:
            self._salida("No hay conversaciones guardadas.")
            return
        self._salida("Conversaciones guardadas:")
        for id_conv in ids:
            self._salida(f"  · {id_conv}")

    def _cmd_nueva(self, _: str) -> None:
        self._agente.nueva_conversacion()
        self._salida(f"🆕 Nueva conversación {self._agente.conversacion.id}")

    def _cmd_limpiar(self, _: str) -> None:
        """Deja la pantalla y el contexto en blanco sin perder la conversación anterior."""
        conversacion = self._agente.conversacion
        if len(conversacion) == 0:
            self._salida("La conversación ya está vacía.")
            return
        repositorio = self._repositorio
        if repositorio is None:
            self._salida("La memoria en disco no está activada: no se limpia para no perder el historial. "
                         "Usa /nueva si quieres descartarla.")
            return
        repositorio.guardar(conversacion)
        anterior = conversacion.id
        self._agente.nueva_conversacion()
        self._salida(f"🧹 Conversación limpia. La anterior sigue guardada: /cargar {anterior}")

    def _cmd_stats(self, _: str) -> None:
        resumen = self._agente.resumen_uso()
        if not resumen:
            self._salida("Todavía no se ha usado ninguna herramienta.")
            return
        self._salida("📊 Uso de herramientas:")
        for nombre, datos in resumen.items():
            self._salida(f"  · {nombre}: {datos['usos']} usos, {datos['fallos']} fallos")
