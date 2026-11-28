"""Capa de servicios: el bucle del agente.

    usuario escribe -> Conversacion.agregar(usuario)
      -> modelo.responder(...)
         ¿pide herramienta? no -> agregar(asistente) -> devolver texto
                            sí -> herramienta.ejecutar(**args)
                                  -> agregar(mensaje de rol "herramienta") -> vuelta al modelo

Esta capa no hace ``print()`` ni ``input()``: solo devuelve valores.
"""

import time
from collections.abc import Iterator

from dominio.excepciones import ArgumentosInvalidos, HerramientaNoEncontrada
from dominio.mensaje import PREFIJO_RESUMEN, Conversacion, Mensaje
from dominio.modelos import Modelo, Respuesta

MAX_VUELTAS = 3
MENSAJE_LIMITE_VUELTAS = (
    "No he conseguido completar la tarea en un número razonable de pasos. "
    "¿Puedes reformular la pregunta?"
)
MENSAJE_SIN_TEXTO = "Lo siento, no he podido generar una respuesta."

# Resumen automático: al superar este porcentaje del límite de tokens se compactan los mensajes antiguos.
UMBRAL_RESUMEN = 0.8
PALABRAS_POR_PREGUNTA_RESUMIDA = 6
MAX_PALABRAS_RESUMEN = 40


class Agente:
    """Orquesta modelo, herramientas, conversación y (opcionalmente) el registro de uso."""

    def __init__(self, modelo, herramientas, registro_uso=None):
        self.modelo = modelo
        self._herramientas = {h.nombre: h for h in herramientas}  # diccionario por nombre
        self._registro = registro_uso  # Nivel 2 (puede ser None)
        self.conversacion = Conversacion()
        self._llamadas: list[tuple[str, dict]] = []

    # --- Bucle principal ---------------------------------------------------
    def procesar(self, texto_usuario: str) -> str:
        """Procesa un mensaje del usuario y devuelve la respuesta final de NEXO.

        Lanza ``HerramientaNoEncontrada`` si el modelo pide una herramienta inexistente
        y ``LimiteContextoSuperado`` si la conversación excede el límite de tokens.
        """
        texto = ""
        for evento in self.procesar_por_pasos(texto_usuario):
            if evento["tipo"] == "final":
                texto = evento["texto"]
        return texto

    def procesar_por_pasos(self, texto_usuario: str) -> Iterator[dict]:
        """Igual que ``procesar()``, pero emite cada paso según ocurre (base del streaming).

        Eventos: ``{"tipo": "herramienta", "nombre", "argumentos", "resultado", "error"}``
        por cada herramienta ejecutada y, al terminar, ``{"tipo": "final", "texto"}``.
        """
        self._llamadas = []
        self.conversacion.agregar(Mensaje("usuario", texto_usuario))

        herramientas = list(self._herramientas.values())
        for _ in range(MAX_VUELTAS):
            respuesta = None
            respuesta_fragmentada = False
            for evento in self.modelo.responder_por_fragmentos(self.conversacion, herramientas):
                if evento["tipo"] == "fragmento":
                    respuesta_fragmentada = True
                    yield {"tipo": "fragmento", "texto": evento["texto"]}
                elif evento["tipo"] == "respuesta":
                    respuesta = evento["respuesta"]
                else:
                    raise RuntimeError("El modelo emitió un evento no reconocido.")
            if respuesta is None:
                raise RuntimeError("El modelo no devolvió una respuesta.")
            if not respuesta.es_llamada_herramienta():
                yield {
                    "tipo": "final",
                    "texto": self._cerrar_con_texto(respuesta.texto or MENSAJE_SIN_TEXTO),
                    "fragmentada": respuesta_fragmentada,
                }
                return
            yield self._ejecutar_herramienta(respuesta)

        yield {
            "tipo": "final",
            "texto": self._cerrar_con_texto(MENSAJE_LIMITE_VUELTAS),
            "fragmentada": False,
        }

    def _cerrar_con_texto(self, texto: str) -> str:
        self.conversacion.agregar(Mensaje("asistente", texto))
        self._compactar_si_hace_falta()
        return texto

    def _compactar_si_hace_falta(self) -> None:
        """Sustituye los intercambios antiguos por un resumen cuando se acerca el límite de tokens.

        Siempre se conserva intacto el último intercambio (desde el último mensaje del usuario).
        """
        conversacion = self.conversacion
        if conversacion.tokens_estimados() <= UMBRAL_RESUMEN * conversacion.limite_tokens:
            return
        mensajes = conversacion.get_mensajes()
        posiciones_usuario = [i for i, m in enumerate(mensajes) if m.rol == "usuario"]
        if not posiciones_usuario:
            return
        inicio_ultimo = posiciones_usuario[-1]
        solo_resumen_previo = inicio_ultimo == 1 and mensajes[0].contenido.startswith(PREFIJO_RESUMEN)
        if inicio_ultimo == 0 or solo_resumen_previo:
            return  # no hay nada antiguo que resumir
        conversacion.compactar(self._resumir(mensajes[:inicio_ultimo]), inicio_ultimo)

    @staticmethod
    def _resumir(mensajes: list[Mensaje]) -> str:
        """Resumen extractivo: el arranque de cada pregunta del usuario (y los resúmenes previos)."""
        fragmentos = []
        for mensaje in mensajes:
            if mensaje.contenido.startswith(PREFIJO_RESUMEN):
                fragmentos.append(mensaje.contenido[len(PREFIJO_RESUMEN):].strip())
            elif mensaje.rol == "usuario":
                fragmentos.append(" ".join(mensaje.contenido.split()[:PALABRAS_POR_PREGUNTA_RESUMIDA]))
        palabras = " | ".join(f for f in fragmentos if f).split()
        return " ".join(palabras[:MAX_PALABRAS_RESUMEN]) or "(sin contenido)"

    def _ejecutar_herramienta(self, respuesta: Respuesta) -> dict:
        """Ejecuta (por polimorfismo) la herramienta pedida y guarda su resultado en la conversación.

        Devuelve el evento ``herramienta`` correspondiente."""
        nombre = respuesta.herramienta
        herramienta = self._herramientas.get(nombre)
        if herramienta is None:
            raise HerramientaNoEncontrada(f"La herramienta '{nombre}' no existe.")

        argumentos = dict(respuesta.argumentos)
        self._llamadas.append((nombre, argumentos))

        exito = True
        inicio = time.perf_counter()
        try:
            resultado = herramienta.ejecutar(**argumentos)
            mensaje = Mensaje.de_herramienta(nombre, resultado)
        except ArgumentosInvalidos as error:
            exito = False
            resultado = str(error)
            mensaje = Mensaje.de_herramienta(nombre, resultado, error=True)
        milisegundos = (time.perf_counter() - inicio) * 1000

        if self._registro is not None:
            self._registro.registrar(nombre, argumentos, exito, milisegundos)
        self.conversacion.agregar(mensaje)
        return {
            "tipo": "herramienta",
            "nombre": nombre,
            "argumentos": argumentos,
            "resultado": resultado,
            "error": not exito,
        }

    # --- Consulta y gestión --------------------------------------------------
    @property
    def llamadas_realizadas(self) -> list[tuple[str, dict]]:
        """Herramientas ejecutadas durante el último ``procesar()``: ``[(nombre, argumentos), ...]``."""
        return [(nombre, dict(args)) for nombre, args in self._llamadas]

    @property
    def nombre_modelo(self) -> str:
        return self.modelo.nombre

    def listar_herramientas(self) -> list[str]:
        return [str(h) for h in self._herramientas.values()]

    def esquemas_herramientas(self) -> list[dict]:
        """Descripción JSON Schema de todas las herramientas (formato de tool calling)."""
        return [h.esquema() for h in self._herramientas.values()]

    def cambiar_modelo(self, modelo) -> None:
        if not isinstance(modelo, Modelo):
            raise TypeError("El modelo debe ser una instancia de Modelo.")
        self.modelo = modelo

    def nueva_conversacion(self) -> None:
        self.conversacion = Conversacion()
        self._llamadas = []

    def cargar_conversacion(self, conversacion: Conversacion) -> None:
        """Sustituye la conversación actual por otra (por ejemplo, una cargada de disco)."""
        if not isinstance(conversacion, Conversacion):
            raise TypeError("Se esperaba un objeto Conversacion.")
        self.conversacion = conversacion
        self._llamadas = []

    def resumen_uso(self) -> dict:
        """Resumen del registro de uso; vacío si no hay registro configurado."""
        return self._registro.resumen() if self._registro is not None else {}

    def resumen_uso_llm(self) -> dict:
        """Totales de tokens y coste del LLM; cero si no hay registro configurado."""
        return self._registro.resumen_llm() if self._registro is not None else {
            "output_tokens": 0,
            "cost": 0.0,
        }
