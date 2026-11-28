"""Punto de entrada de NEXO: aquí (y solo aquí) se conectan todas las piezas."""

from pathlib import Path

from dominio.herramientas import BuscadorFAQ, Calculadora, ConsultaStock, ConversorMoneda, Reloj
from dominio.modelos import ModeloEco, ModeloReglas
from persistencia.registro_uso import RegistroUso
from persistencia.repositorio_conversaciones import RepositorioConversaciones
from presentacion.chat_consola import ChatConsola
from servicios.agente import Agente

# Los datos se guardan junto a main.py, se ejecute desde donde se ejecute.
DIRECTORIO_DATOS = Path(__file__).resolve().parent / "datos"


def construir_herramientas() -> list:
    """Herramientas disponibles para el agente (las usan la consola y la web)."""
    return [Calculadora(), ConversorMoneda(), BuscadorFAQ(), ConsultaStock(), Reloj()]


def main() -> None:
    herramientas = construir_herramientas()
    modelo_reglas = ModeloReglas()
    agente = Agente(modelo_reglas, herramientas, RegistroUso(DIRECTORIO_DATOS / "uso.csv"))
    repositorio = RepositorioConversaciones(DIRECTORIO_DATOS / "conversaciones")
    modelos = {"eco": ModeloEco(), "reglas": modelo_reglas}
    ChatConsola(agente, repositorio, modelos).iniciar()


if __name__ == "__main__":
    main()
