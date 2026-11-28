"""Tests de las mejoras: nuevas herramientas, esquemas JSON, encadenado, resumen automático y robustez."""

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from dominio.herramientas import BuscadorFAQ, Calculadora, ConsultaStock, ConversorMoneda, Reloj
from dominio.mensaje import Conversacion, Mensaje
from dominio.modelos import Modelo, ModeloEco, ModeloReglas
from persistencia.repositorio_conversaciones import RepositorioConversaciones
from presentacion.chat_consola import ChatConsola
from servicios.agente import Agente


def todas():
    return [Calculadora(), ConversorMoneda(), BuscadorFAQ(), ConsultaStock(), Reloj()]


class TestNuevasHerramientas(unittest.TestCase):
    def test_reloj(self):
        reloj = Reloj(reloj=lambda: datetime(2026, 10, 18, 9, 5))
        self.assertEqual(reloj.ejecutar(), "Hoy es domingo 18 de octubre de 2026 y son las 09:05.")

    def test_consulta_stock(self):
        stock = ConsultaStock()
        self.assertEqual(stock.ejecutar(producto="cuántas unidades quedan de ssd"), "SSD 1 TB: 14 unidades en stock.")
        self.assertEqual(stock.ejecutar(producto="ram ddr5"), "RAM DDR5 16 GB: agotado.")
        self.assertEqual(stock.ejecutar(producto="una nevera"), "No encontrado")

    def test_esquema(self):
        esquema = Calculadora().esquema()
        self.assertEqual(esquema["name"], "calculadora")
        self.assertEqual(esquema["input_schema"]["required"], ["a", "b", "operacion"])
        self.assertEqual(esquema["input_schema"]["properties"]["operacion"]["enum"], ["+", "-", "*", "/"])
        self.assertEqual(Reloj().esquema()["input_schema"]["properties"], {})
        json.dumps(esquema)  # serializable

    def test_esquema_es_una_copia(self):
        herramienta = Calculadora()
        herramienta.esquema()["input_schema"]["properties"].clear()
        self.assertIn("a", herramienta.esquema()["input_schema"]["properties"])


class TestEncadenado(unittest.TestCase):
    def test_dos_herramientas_en_una_pregunta(self):
        agente = Agente(ModeloReglas(), todas())
        respuesta = agente.procesar("convierte 100 USD a euros y multiplícalo por 3")
        self.assertEqual(respuesta, "100 USD = 92.00 EUR; y luego 92 * 3 = 276. ¿Necesitas algo más?")
        self.assertEqual([n for n, _ in agente.llamadas_realizadas], ["conversor_moneda", "calculadora"])

    def test_otras_operaciones_encadenadas(self):
        agente = Agente(ModeloReglas(), todas())
        self.assertIn("92 / 2 = 46", agente.procesar("pasa 100 dólares a euros y divídelo entre 2"))

    def test_conversion_sola_no_encadena(self):
        agente = Agente(ModeloReglas(), todas())
        self.assertEqual(agente.procesar("cuánto son 250 USD en euros"), "250 USD = 230.00 EUR.")
        self.assertEqual(len(agente.llamadas_realizadas), 1)

    def test_nuevas_herramientas_desde_el_modelo(self):
        agente = Agente(ModeloReglas(), todas())
        self.assertIn("unidades en stock", agente.procesar("¿cuántas unidades de teclado mecánico quedan?"))
        self.assertIn("Hoy es", agente.procesar("¿qué hora es?"))
        self.assertIn("catálogo", agente.procesar("¿queda stock de nevera?"))


class TestResumenAutomatico(unittest.TestCase):
    def test_compactar(self):
        conversacion = Conversacion()
        for texto in ("uno dos", "tres cuatro", "cinco seis"):
            conversacion.agregar(Mensaje("usuario", texto))
        conversacion.compactar("resumen breve", 2)
        self.assertEqual([m.contenido for m in conversacion.get_mensajes()],
                         ["[resumen] resumen breve", "cinco seis"])
        self.assertEqual(conversacion.tokens_estimados(), round(5 * 1.3))  # contador sincronizado
        with self.assertRaises(ValueError):
            conversacion.compactar("x", 0)

    def test_el_agente_resume_al_superar_el_80_por_ciento(self):
        agente = Agente(ModeloEco(), todas())
        agente.cargar_conversacion(Conversacion(limite_tokens=100))
        for _ in range(12):  # sin resumen, esto superaría el límite y lanzaría LimiteContextoSuperado
            agente.procesar("mensaje numero uno dos tres")
        mensajes = agente.conversacion.get_mensajes()
        self.assertTrue(mensajes[0].contenido.startswith("[resumen]"))
        self.assertLessEqual(agente.conversacion.tokens_estimados(), 100)
        self.assertEqual(mensajes[-1].contenido, "Has dicho: mensaje numero uno dos tres")

    def test_contador_coherente_tras_cargar(self):
        conversacion = Conversacion()
        conversacion.agregar(Mensaje("usuario", "a b c d e f g h i j"))
        copia = Conversacion.from_dict(conversacion.to_dict())
        self.assertEqual(copia.tokens_estimados(), conversacion.tokens_estimados())


class TestRobustez(unittest.TestCase):
    def test_guardado_atomico_sin_residuos(self):
        with tempfile.TemporaryDirectory() as tmp:
            repositorio = RepositorioConversaciones(tmp)
            conversacion = Conversacion()
            conversacion.agregar(Mensaje("usuario", "hola"))
            repositorio.guardar(conversacion)
            repositorio.guardar(conversacion)  # sobrescribir también funciona
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), [f"{conversacion.id}.json"])

    def test_el_chat_sobrevive_a_un_fallo_inesperado(self):
        class ModeloRoto(Modelo):
            def __init__(self):
                super().__init__("Roto")

            def responder(self, conversacion, herramientas):
                raise RuntimeError("fallo interno")

        cola, salida = iter(["hola", "/salir"]), []
        chat = ChatConsola(Agente(ModeloRoto(), todas()), entrada=lambda _: next(cola), salida=salida.append)
        chat.iniciar()
        self.assertTrue(any("Error inesperado (RuntimeError)" in linea for linea in salida))
        self.assertTrue(any("Hasta pronto" in linea for linea in salida))

    def test_comando_esquemas(self):
        cola, salida = iter(["/esquemas", "/salir"]), []
        ChatConsola(Agente(ModeloEco(), todas()), entrada=lambda _: next(cola), salida=salida.append).iniciar()
        volcado = next(linea for linea in salida if linea.startswith("["))
        self.assertEqual(len(json.loads(volcado)), 5)


if __name__ == "__main__":
    unittest.main()
