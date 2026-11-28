"""Punto de entrada web de NEXO: arranca la API y sirve el frontend compilado.

    python main_web.py            ->  http://127.0.0.1:8000

Igual que ``main.py``, aquí se conectan todas las piezas.
"""

import os
from pathlib import Path

from main import DIRECTORIO_DATOS, construir_herramientas
from dominio.modelos import ModeloEco, ModeloLLM, ModeloReglas
from persistencia.registro_uso import RegistroUso
from persistencia.repositorio_conversaciones import RepositorioConversaciones
from presentacion.api import crear_app
from servicios.agente import Agente
from servicios.gestor_conversaciones import GestorConversaciones

RAIZ = Path(__file__).resolve().parent
ORIGENES_CORS = [o for o in os.environ.get("NEXO_CORS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o]


def construir_gestor(directorio_datos: Path = DIRECTORIO_DATOS) -> GestorConversaciones:
    modelos = {"reglas": ModeloReglas(), "eco": ModeloEco()}
    registro_uso = RegistroUso(directorio_datos / "uso.csv")
    no_disponibles: dict[str, str] = {}
    if os.getenv("LLM_API_KEY", "").strip():
        modelos["llm"] = ModeloLLM(registrar_uso=registro_uso.registrar_llm)
    else:
        no_disponibles["llm"] = "Configura LLM_API_KEY en el archivo .env del servidor."
    repositorio = RepositorioConversaciones(directorio_datos / "conversaciones")
    return GestorConversaciones(
        lambda: Agente(modelos["reglas"], construir_herramientas(), registro_uso), repositorio, modelos, no_disponibles
    )


app = crear_app(construir_gestor(), ORIGENES_CORS, RAIZ / "frontend" / "dist")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("NEXO_PUERTO", "8000")))
