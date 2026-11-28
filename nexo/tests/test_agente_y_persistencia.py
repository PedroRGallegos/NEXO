"""Tests del agente, la persistencia y el chat (con datos en carpetas temporales)."""

import csv
import re
import tempfile
import unittest
from pathlib import Path

from dominio.excepciones import ConversacionNoEncontrada, ErrorPersistencia, HerramientaNoEncontrada
from dominio.herramientas import BuscadorFAQ, Calculadora, ConversorMoneda
from dominio.mensaje import Conversacion, Mensaje
from dominio.modelos import Modelo, ModeloEco, ModeloReglas, Respuesta
from persistencia.registro_uso import RegistroUso
from persistencia.repositorio_conversaciones import RepositorioConversaciones
from presentacion.chat_consola import ChatConsola
from servicios.agente import MAX_VUELTAS, Agente


def herramientas():
    return [Calculadora(), ConversorMoneda(), BuscadorFAQ()]


class ModeloQuePideSiempre(Modelo):
    """Modelo de prueba que pide una herramienta en bucle."""

    def __init__(self, herramienta, argumentos):
        super().__init__("Bucle")
        self._respuesta = Respuesta(herramienta=herramienta, argumentos=argumentos)

    def responder(self, conversacion, herramientas):
        return self._respuesta


class TestAgente(unittest.TestCase):
    def test_flujo_con_herramienta(self):
        agente = Agente(ModeloReglas(), herramientas())
        self.assertEqual(agente.procesar("3 * 4"), "El resultado es 3 * 4 = 12. ¿Necesitas algo más?")
        self.assertEqual(agente.llamadas_realizadas, [("calculadora", {"a": 3, "b": 4, "operacion": "*"})])
        roles = [m.rol for m in agente.conversacion.get_mensajes()]
        self.assertEqual(roles, ["usuario", "herramienta", "asistente"])

    def test_herramienta_inexistente(self):
        agente = Agente(ModeloQuePideSiempre("no_existe", {}), herramientas())
        with self.assertRaises(HerramientaNoEncontrada):
            agente.procesar("hola")

    def test_error_de_herramienta_no_rompe(self):
        agente = Agente(ModeloReglas(), herramientas())
        self.assertIn("dividir entre 0", agente.procesar("5 / 0"))

    def test_limite_de_vueltas(self):
        agente = Agente(ModeloQuePideSiempre("calculadora", {"a": 1, "b": 1, "operacion": "+"}), herramientas())
        agente.procesar("hola")
        self.assertEqual(len(agente.llamadas_realizadas), MAX_VUELTAS)

    def test_cambiar_modelo_y_nueva_conversacion(self):
        agente = Agente(ModeloReglas(), herramientas())
        agente.cambiar_modelo(ModeloEco())
        self.assertEqual(agente.procesar("3 * 4"), "Has dicho: 3 * 4")
        self.assertEqual(agente.llamadas_realizadas, [])
        antigua = agente.conversacion.id
        agente.nueva_conversacion()
        self.assertNotEqual(agente.conversacion.id, antigua)
        self.assertEqual(len(agente.conversacion), 0)
        with self.assertRaises(TypeError):
            agente.cambiar_modelo("no soy un modelo")

    def test_listar_herramientas(self):
        self.assertEqual(len(Agente(ModeloEco(), herramientas()).listar_herramientas()), 3)


class TestPersistencia(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.carpeta = Path(self._tmp.name)

    def test_guardar_y_cargar(self):
        repositorio = RepositorioConversaciones(self.carpeta / "conv")
        conversacion = Conversacion()
        conversacion.agregar(Mensaje("usuario", "¿Cuánto tarda el envío? ñ"))
        repositorio.guardar(conversacion)
        self.assertEqual(repositorio.listar(), [conversacion.id])
        self.assertEqual(repositorio.cargar(conversacion.id).to_dict(), conversacion.to_dict())

    def test_errores_de_carga(self):
        repositorio = RepositorioConversaciones(self.carpeta)
        with self.assertRaises(ConversacionNoEncontrada):
            repositorio.cargar("noexiste")
        with self.assertRaises(ConversacionNoEncontrada):
            repositorio.cargar("../../etc/passwd")
        (self.carpeta / "roto.json").write_text("{esto no es json", encoding="utf-8")
        with self.assertRaises(ErrorPersistencia):
            repositorio.cargar("roto")
        (self.carpeta / "incompleto.json").write_text('{"id": "x"}', encoding="utf-8")
        with self.assertRaises(ErrorPersistencia):
            repositorio.cargar("incompleto")

    def test_registro_uso_y_resumen(self):
        ruta = self.carpeta / "uso.csv"
        agente = Agente(ModeloReglas(), herramientas(), RegistroUso(ruta))
        agente.procesar("3 * 4")
        agente.procesar("5 / 0")
        agente.procesar("cuánto tarda el envío")
        self.assertEqual(
            agente.resumen_uso(),
            {"calculadora": {"usos": 2, "fallos": 1}, "buscador_faq": {"usos": 1, "fallos": 0}},
        )
        cabecera = ruta.read_text(encoding="utf-8").splitlines()[0]
        self.assertEqual(
            cabecera,
            "timestamp,question,output_tokens,cost,fecha,herramienta,argumentos,exito,milisegundos",
        )
        # Reabrir no duplica la cabecera ni borra datos
        RegistroUso(ruta)
        self.assertEqual(ruta.read_text(encoding="utf-8").count("timestamp,question"), 1)
        self.assertEqual(RegistroUso(ruta).resumen()["calculadora"]["usos"], 2)

    def test_migra_el_csv_de_herramientas_existente_y_conserva_sus_filas(self):
        ruta = self.carpeta / "uso.csv"
        ruta.write_text(
            "fecha,herramienta,argumentos,exito,milisegundos\n"
            "2026-01-02T03:04:05,calculadora,\"{'a': 1}\",True,2.5\n",
            encoding="utf-8",
        )
        registro = RegistroUso(ruta)
        self.assertEqual(registro.resumen(), {"calculadora": {"usos": 1, "fallos": 0}})
        self.assertEqual(registro.resumen_llm(), {"output_tokens": 0, "cost": 0.0})
        with ruta.open(newline="", encoding="utf-8") as fichero:
            fila = next(csv.DictReader(fichero))
        self.assertEqual(fila["fecha"], "2026-01-02T03:04:05")
        self.assertEqual(fila["herramienta"], "calculadora")

    def test_resumen_vacio(self):
        self.assertEqual(Agente(ModeloEco(), herramientas()).resumen_uso(), {})


class TestChat(unittest.TestCase):
    def ejecutar(self, entradas, tmp):
        cola = iter(entradas)
        salida = []
        agente = Agente(ModeloReglas(), herramientas(), RegistroUso(Path(tmp) / "uso.csv"))
        chat = ChatConsola(
            agente,
            RepositorioConversaciones(Path(tmp) / "conv"),
            {"eco": ModeloEco(), "reglas": ModeloReglas()},
            entrada=lambda _: next(cola),
            salida=salida.append,
        )
        chat.iniciar()
        return agente, "\n".join(salida)

    def test_limpiar_guarda_la_conversacion_y_empieza_de_cero(self):
        with tempfile.TemporaryDirectory() as tmp:
            agente, texto = self.ejecutar(["hola", "/limpiar", "/salir"], tmp)
            anterior = re.search(r"/cargar (\w+)", texto).group(1)
            self.assertEqual(len(agente.conversacion), 0)
            self.assertNotEqual(agente.conversacion.id, anterior)
            self.assertIn(anterior, RepositorioConversaciones(Path(tmp) / "conv").listar())

    def test_limpiar_con_la_conversacion_vacia_no_crea_otra(self):
        with tempfile.TemporaryDirectory() as tmp:
            agente, texto = self.ejecutar(["/limpiar", "/salir"], tmp)
            self.assertIn("ya está vacía", texto)
            self.assertEqual(RepositorioConversaciones(Path(tmp) / "conv").listar(), [])

    def test_limpiar_sin_memoria_en_disco_no_pierde_la_conversacion(self):
        cola, salida = iter(["hola", "/limpiar", "/salir"]), []
        agente = Agente(ModeloEco(), herramientas())
        ChatConsola(agente, entrada=lambda _: next(cola), salida=salida.append).iniciar()
        self.assertEqual(len(agente.conversacion), 2)
        self.assertIn("no se limpia para no perder el historial", "\n".join(salida))

    def test_ejemplo_de_ejecucion(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, texto = self.ejecutar(
                ["hola", "si compro 3 * 79.9 cuánto pago?", "cuánto son 250 USD en euros",
                 "cuánto tarda el envío?", "/modelo eco", "hola", "/guardar", "/salir"], tmp)
        for esperado in (
            "NEXO > ¡Hola! Soy NEXO, ¿en qué te ayudo?",
            "🔧 calculadora(a=3, b=79.9, operacion='*')",
            "NEXO > El resultado es 3 * 79.9 = 239.7. ¿Necesitas algo más?",
            "🔧 conversor_moneda(cantidad=250, origen='USD', destino='EUR')",
            "NEXO > 250 USD = 230.00 EUR.",
            "🔧 buscador_faq(pregunta='cuánto tarda el envío?')",
            "NEXO > Según nuestra información: Los envíos tardan 24-48 h en península",
            "✔ Modelo cambiado a ModeloEco",
            "NEXO > Has dicho: hola",
            "💾 Conversación",
        ):
            self.assertIn(esperado, texto)

    def test_guardar_y_cargar_en_otra_sesion(self):
        with tempfile.TemporaryDirectory() as tmp:
            agente, _ = self.ejecutar(["hola", "/guardar", "/salir"], tmp)
            id_guardado = agente.conversacion.id
            nuevo, texto = self.ejecutar([f"/cargar {id_guardado}", "/historial", "/salir"], tmp)
        self.assertEqual(len(nuevo.conversacion), 2)
        self.assertIn("cargada (2 mensajes)", texto)
        self.assertIn("tokens estimados", texto)

    def test_el_chat_no_se_cierra_con_errores(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, texto = self.ejecutar(
                ["/cargar zzz", "/cargar", "/cargar ../x", "/comando_raro", "/modelo xx", "", "5 / 0", "/stats", "/salir"], tmp)
        self.assertIn("No existe la conversación 'zzz'", texto)
        self.assertIn("Uso: /cargar <id>", texto)
        self.assertIn("Comando desconocido", texto)
        self.assertIn("calculadora: 1 usos, 1 fallos", texto)
        self.assertIn("¡Hasta pronto!", texto)

    def test_limite_de_contexto_muestra_aviso(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, texto = self.ejecutar(["palabra " * 400, "/salir"], tmp)
        self.assertIn("/nueva", texto)

    def test_ctrl_d_termina_sin_error(self):
        agente = Agente(ModeloEco(), herramientas())
        chat = ChatConsola(agente, entrada=lambda _: (_ for _ in ()).throw(EOFError), salida=lambda _: None)
        chat.iniciar()

    def test_sin_repositorio(self):
        salida = []
        cola = iter(["/guardar", "/salir"])
        ChatConsola(Agente(ModeloEco(), herramientas()), entrada=lambda _: next(cola), salida=salida.append).iniciar()
        self.assertTrue(any("no está activada" in linea for linea in salida))


if __name__ == "__main__":
    unittest.main()
