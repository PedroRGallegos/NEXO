"""Tests de ``Agente.procesar_por_pasos`` y ``GestorConversaciones`` (sin FastAPI)."""

import tempfile
import unittest
from pathlib import Path

from dominio.excepciones import ConversacionNoEncontrada, ModeloNoDisponible
from dominio.herramientas import Calculadora, ConversorMoneda
from dominio.modelos import Modelo, ModeloEco, ModeloReglas
from persistencia.repositorio_conversaciones import RepositorioConversaciones
from servicios.agente import Agente
from servicios.gestor_conversaciones import GestorConversaciones, resumir


class PruebaProcesarPorPasos(unittest.TestCase):
    def agente(self):
        return Agente(ModeloReglas(), [Calculadora(), ConversorMoneda()])

    def test_emite_herramientas_en_orden_y_un_unico_final(self):
        eventos = list(self.agente().procesar_por_pasos("convierte 100 USD a euros y multiplícalo por 3"))
        self.assertEqual([e["tipo"] for e in eventos], ["herramienta", "herramienta", "final"])
        self.assertEqual([e["nombre"] for e in eventos[:2]], ["conversor_moneda", "calculadora"])
        self.assertIn("276", eventos[-1]["texto"])

    def test_el_evento_de_herramienta_marca_los_errores(self):
        evento = next(iter(self.agente().procesar_por_pasos("5 / 0")))
        self.assertTrue(evento["error"])
        self.assertIn("dividir", evento["resultado"])

    def test_procesar_devuelve_el_mismo_texto_que_el_evento_final(self):
        a, b = self.agente(), self.agente()
        texto = a.procesar("2 + 3")
        self.assertEqual(texto, list(b.procesar_por_pasos("2 + 3"))[-1]["texto"])


class PruebaGestor(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.modelos = {"reglas": ModeloReglas(), "eco": ModeloEco()}
        self.repo = RepositorioConversaciones(Path(tmp.name))
        self.gestor = GestorConversaciones(lambda: Agente(self.modelos["reglas"], [Calculadora()]), self.repo, self.modelos)

    def test_cada_conversacion_tiene_su_agente(self):
        a, b = self.gestor.crear(), self.gestor.crear()
        self.assertIsNot(a, b)
        self.assertIs(self.gestor.obtener(a.conversacion.id), a)

    def test_recupera_de_disco_y_lista_la_mas_reciente_primero(self):
        a = self.gestor.crear(); a.procesar("1 + 1"); self.gestor.guardar(a)
        b = self.gestor.crear(); b.procesar("2 + 2"); self.gestor.guardar(b)
        otro = GestorConversaciones(lambda: Agente(self.modelos["reglas"], [Calculadora()]), self.repo, self.modelos)
        self.assertEqual(len(otro.obtener(a.conversacion.id).conversacion), 3)
        self.assertEqual([r["id"] for r in otro.listar()], [b.conversacion.id, a.conversacion.id])

    def test_errores(self):
        with self.assertRaises(ConversacionNoEncontrada):
            self.gestor.obtener("noexiste")
        with self.assertRaises(ModeloNoDisponible):
            self.gestor.cambiar_modelo(self.gestor.crear(), "gpt-99")

    def test_titulo_recortado_y_conversacion_vacia(self):
        agente = self.gestor.crear()
        self.assertEqual(resumir(agente.conversacion)["titulo"], "Conversación vacía")
        agente.procesar("hola " + "x" * 100)
        self.assertLessEqual(len(resumir(agente.conversacion)["titulo"]), 40)

    def test_el_fichero_danado_no_rompe_el_listado(self):
        a = self.gestor.crear(); a.procesar("1 + 1"); self.gestor.guardar(a)
        (self.repo._carpeta / "roto.json").write_text("{no es json", encoding="utf-8")
        self.assertEqual([r["id"] for r in self.gestor.listar()], [a.conversacion.id])


class _LLMFalso(Modelo):
    """Sustituto remoto sin red para probar el catálogo."""

    remoto = True


class PruebaCatalogoModelos(unittest.TestCase):
    MOTIVO = "Configura LLM_API_KEY en el archivo .env del servidor."

    def _gestor(self, modelos, no_disponibles=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        repo = RepositorioConversaciones(Path(tmp.name))
        return GestorConversaciones(
            lambda: Agente(modelos["reglas"], [Calculadora()]), repo, modelos, no_disponibles
        )

    def test_sin_llm_aparece_no_disponible_y_al_final(self):
        gestor = self._gestor({"reglas": ModeloReglas(), "eco": ModeloEco()}, {"llm": self.MOTIVO})
        catalogo = gestor.catalogo_modelos()
        self.assertEqual([m["id"] for m in catalogo], ["reglas", "eco", "llm"])
        self.assertEqual(catalogo[0], {"id": "reglas", "nombre": "ModeloReglas", "tipo": "local",
                                       "disponible": True, "motivo": None, "detalle": None})
        self.assertEqual(catalogo[2], {"id": "llm", "nombre": "ModeloLLM", "tipo": "remoto",
                                       "disponible": False, "motivo": self.MOTIVO, "detalle": None})

    def test_con_llm_disponible_y_detalle_es_el_modelo_del_proveedor(self):
        modelos = {"reglas": ModeloReglas(), "eco": ModeloEco(), "llm": _LLMFalso("gpt-4o")}
        catalogo = self._gestor(modelos).catalogo_modelos()
        self.assertEqual([m["id"] for m in catalogo], ["reglas", "eco", "llm"])
        self.assertEqual(catalogo[2]["tipo"], "remoto")
        self.assertTrue(catalogo[2]["disponible"])
        self.assertIsNone(catalogo[2]["motivo"])
        self.assertEqual(catalogo[2]["detalle"], "gpt-4o")

    def test_los_remotos_van_despues_aunque_se_registren_antes(self):
        modelos = {"llm": _LLMFalso("x"), "reglas": ModeloReglas(), "eco": ModeloEco()}
        gestor = self._gestor(modelos)
        self.assertEqual([m["id"] for m in gestor.catalogo_modelos()], ["reglas", "eco", "llm"])

    def test_cambiar_a_modelo_no_disponible_explica_el_motivo(self):
        gestor = self._gestor({"reglas": ModeloReglas(), "eco": ModeloEco()}, {"llm": self.MOTIVO})
        with self.assertRaises(ModeloNoDisponible) as ctx:
            gestor.cambiar_modelo(gestor.crear(), "llm")
        self.assertEqual(str(ctx.exception), f"Modelo 'llm' no disponible. {self.MOTIVO}")
        with self.assertRaises(ModeloNoDisponible) as ctx:
            gestor.cambiar_modelo(gestor.crear(), "gpt-99")
        self.assertIn("Opciones: reglas, eco", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
