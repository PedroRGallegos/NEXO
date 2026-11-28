"""Capa de presentación web: API HTTP (FastAPI) sobre el agente.

Solo traduce HTTP a llamadas al ``GestorConversaciones`` y devuelve JSON o SSE.
No contiene lógica de negocio.

Errores: siempre ``{"error": {"codigo": ..., "mensaje": ...}}``, sin detalles internos.
"""

import json
import logging
import math
import queue
import re
import threading
from collections.abc import Iterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as ErrorHttp

from dominio.excepciones import (
    ArgumentosInvalidos,
    ConversacionNoEncontrada,
    ErrorAgente,
    ErrorPersistencia,
    ErrorProveedorLLM,
    HerramientaNoEncontrada,
    LimiteContextoSuperado,
    ModeloNoDisponible,
)
from dominio.mensaje import Conversacion
from dominio.modelos import PeticionInvalida
from presentacion.esquemas_api import PeticionMensaje, PeticionModelo
from servicios.agente import Agente
from servicios.gestor_conversaciones import GestorConversaciones

registro = logging.getLogger("nexo.api")

# Excepción de dominio -> (código HTTP, código estable para el frontend, mensaje público)
# El mensaje es None cuando se puede mostrar el de la propia excepción.
_ERRORES = {
    ConversacionNoEncontrada: (404, "conversacion_no_encontrada", None),
    LimiteContextoSuperado: (409, "limite_contexto", None),
    ModeloNoDisponible: (422, "modelo_no_disponible", None),
    ErrorProveedorLLM: (502, "error_proveedor", None),  # el texto lo escribe ModeloLLM: HTTP + motivo del proveedor, sin claves
    ArgumentosInvalidos: (422, "argumentos_invalidos", None),
    HerramientaNoEncontrada: (500, "herramienta_no_encontrada", "El asistente pidió una herramienta que no existe."),
    PeticionInvalida: (422, "peticion_invalida", None),
    ErrorPersistencia: (500, "error_almacenamiento", "No se pudo acceder al almacenamiento de conversaciones."),
}
_PARTES_TEXTO = re.compile(r"\S+\s*")


def _clasificar(error: Exception) -> tuple[int, str, str]:
    for tipo, (estado, codigo, mensaje) in _ERRORES.items():
        if isinstance(error, tipo):
            return estado, codigo, mensaje or str(error)
    return 500, "error_interno", "Error interno del servidor."


def _respuesta_error(estado: int, codigo: str, mensaje: str) -> JSONResponse:
    return JSONResponse(status_code=estado, content={"error": {"codigo": codigo, "mensaje": mensaje}})


def _json_seguro(valor):
    """Cambia ``inf``/``nan`` por texto: no existen en JSON y rompían la respuesta (p. ej. un número de 400 cifras)."""
    if isinstance(valor, float) and not math.isfinite(valor):
        return str(valor)
    if isinstance(valor, dict):
        return {clave: _json_seguro(v) for clave, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_json_seguro(v) for v in valor]
    return valor


def _evento_sse(evento: str, datos: dict) -> str:
    return f"event: {evento}\ndata: {json.dumps(_json_seguro(datos), ensure_ascii=False)}\n\n"


def _estado_conversacion(gestor: GestorConversaciones, agente: Agente) -> dict:
    conversacion = agente.conversacion
    return {
        "id": conversacion.id,
        "modelo": gestor.id_modelo(agente),
        "mensajes": [m.to_dict() for m in conversacion.get_mensajes()],
        "tokens_estimados": conversacion.tokens_estimados(),
        "limite_tokens": conversacion.limite_tokens,
    }


def _estadisticas(gestor: GestorConversaciones) -> dict:
    """Cifras calculadas sobre las conversaciones guardadas y el registro de uso real."""
    peticiones = entrada = salida = 0
    conversaciones = gestor.todas_guardadas()
    for conversacion in conversaciones:
        for mensaje in conversacion.get_mensajes():
            tokens = round(len(mensaje.contenido.split()) * Conversacion.TOKENS_POR_PALABRA)
            if mensaje.rol == "asistente":
                salida += tokens
            else:
                entrada += tokens
                peticiones += mensaje.rol == "usuario"
    uso_llm = gestor.resumen_uso_llm()
    return {
        "conversaciones": len(conversaciones),
        "peticiones": peticiones,
        "tokens_entrada_estimados": entrada,
        "tokens_salida_estimados": salida,
        "tokens_salida_llm": uso_llm["output_tokens"],
        "coste_eur": uso_llm["cost"],
        "nota": "Tokens estimados (palabras × 1,3) sobre el historial guardado; "
                "el coste y tokens reales del LLM se leen de uso.csv.",
        "herramientas": gestor.resumen_uso(),
    }


def crear_app(
    gestor: GestorConversaciones,
    origenes_cors: list[str] | None = None,
    carpeta_frontend: Path | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def ciclo_vida(_: FastAPI):
        yield
        for modelo in gestor.modelos.values():
            cerrar = getattr(modelo, "cerrar", None)
            if callable(cerrar):
                cerrar()

    app = FastAPI(
        title="NEXO · API",
        version="1.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=ciclo_vida,
    )
    if origenes_cors:
        app.add_middleware(
            CORSMiddleware, allow_origins=origenes_cors, allow_methods=["GET", "POST", "PATCH"], allow_headers=["Content-Type"]
        )

    # --- Errores ---------------------------------------------------------------
    @app.exception_handler(RequestValidationError)
    async def _peticion_invalida(_: Request, error: RequestValidationError):
        detalle = "; ".join(f"{'.'.join(map(str, e['loc'][1:]))}: {e['msg']}" for e in error.errors())
        return _respuesta_error(422, "peticion_invalida", detalle or "Petición no válida.")

    @app.exception_handler(ErrorHttp)
    async def _error_http(_: Request, error: ErrorHttp):
        codigos = {404: "no_encontrado", 405: "metodo_no_permitido"}
        return _respuesta_error(error.status_code, codigos.get(error.status_code, "error_http"), "Recurso no disponible.")

    @app.exception_handler(ErrorAgente)
    @app.exception_handler(Exception)
    async def _error_controlado(_: Request, error: Exception):
        estado, codigo, mensaje = _clasificar(error)
        if estado >= 500:
            registro.exception("Error al atender la petición", exc_info=error)
        return _respuesta_error(estado, codigo, mensaje)

    # --- Información -------------------------------------------------------------
    @app.get("/api/salud")
    def salud() -> dict:
        return {"estado": "ok"}

    @app.get("/api/modelos")
    def modelos() -> list[dict]:
        return gestor.catalogo_modelos()

    @app.get("/api/herramientas")
    def herramientas() -> list[dict]:
        return [
            {"nombre": e["name"], "descripcion": e["description"], "parametros": e["input_schema"]["properties"]}
            for e in gestor.esquemas_herramientas()
        ]

    @app.get("/api/estadisticas")
    def estadisticas() -> dict:
        return _estadisticas(gestor)

    # --- Conversaciones ----------------------------------------------------------
    @app.get("/api/conversaciones")
    def listar() -> list[dict]:
        return gestor.listar()

    @app.post("/api/conversaciones", status_code=201)
    def crear() -> dict:
        return _estado_conversacion(gestor, gestor.crear())

    @app.get("/api/conversaciones/{id_conv}")
    def obtener(id_conv: str) -> dict:
        return _estado_conversacion(gestor, gestor.obtener(id_conv))

    @app.patch("/api/conversaciones/{id_conv}")
    def cambiar_modelo(id_conv: str, peticion: PeticionModelo) -> dict:
        agente = gestor.obtener(id_conv)
        with gestor.acceso_exclusivo(id_conv):
            gestor.cambiar_modelo(agente, peticion.modelo)
        return _estado_conversacion(gestor, agente)

    @app.post("/api/conversaciones/{id_conv}/mensajes")
    def enviar(id_conv: str, peticion: PeticionMensaje) -> dict:
        agente = gestor.obtener(id_conv)
        with gestor.acceso_exclusivo(id_conv):
            respuesta = agente.procesar(peticion.texto)
            llamadas = [{"nombre": n, "argumentos": _json_seguro(a)} for n, a in agente.llamadas_realizadas]
            gestor.guardar(agente)
            return {"respuesta": respuesta, "herramientas_usadas": llamadas,
                    "conversacion": _estado_conversacion(gestor, agente)}

    @app.post("/api/conversaciones/{id_conv}/mensajes/stream")
    def enviar_stream(id_conv: str, peticion: PeticionMensaje) -> StreamingResponse:
        agente = gestor.obtener(id_conv)  # errores de "no existe" salen como HTTP normal
        return StreamingResponse(
            _flujo_sse(gestor, agente, id_conv, peticion.texto),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    if carpeta_frontend is not None and carpeta_frontend.is_dir():
        app.mount("/", StaticFiles(directory=carpeta_frontend, html=True), name="frontend")
    return app


def _flujo_sse(gestor: GestorConversaciones, agente: Agente, id_conv: str, texto: str) -> Iterator[str]:
    """Emite pasos y fragmentos del modelo; ``fin`` contiene el estado actualizado.

    Los modelos locales devuelven el texto completo y se dividen en fragmentos aquí. El
    modelo LLM, en cambio, transmite cada fragmento de la respuesta del proveedor.

    El trabajo corre en un hilo propio que es quien toma y suelta el cerrojo de la conversación.
    Si el cliente corta la conexión, el hilo termina igualmente (la conversación se guarda) y el
    cerrojo se libera al momento, en lugar de quedar atado al generador abandonado.
    """
    cola: queue.SimpleQueue = queue.SimpleQueue()
    terminado = object()

    def trabajar() -> None:
        try:
            with gestor.acceso_exclusivo(id_conv):
                for evento in agente.procesar_por_pasos(texto):
                    if evento["tipo"] == "herramienta":
                        cola.put(_evento_sse("herramienta", evento))
                    elif evento["tipo"] == "fragmento":
                        cola.put(_evento_sse("fragmento", {"texto": evento["texto"]}))
                    elif not evento.get("fragmentada", False):
                        for parte in _PARTES_TEXTO.findall(evento["texto"]):
                            cola.put(_evento_sse("fragmento", {"texto": parte}))
                gestor.guardar(agente)
                cola.put(_evento_sse("fin", _estado_conversacion(gestor, agente)))
        except Exception as error:  # el flujo ya empezó: el error viaja como evento
            estado, codigo, mensaje = _clasificar(error)
            if estado >= 500:
                registro.exception("Error durante el streaming", exc_info=error)
            cola.put(_evento_sse("error", {"codigo": codigo, "mensaje": mensaje}))
        finally:
            cola.put(terminado)

    threading.Thread(target=trabajar, name=f"sse-{id_conv}", daemon=True).start()
    while (elemento := cola.get()) is not terminado:
        yield elemento
