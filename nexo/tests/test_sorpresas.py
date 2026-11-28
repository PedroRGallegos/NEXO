"""Las sorpresas del chat: respuesta fija y misma detección que el frontend (huevos.test.ts)."""

import unittest

from dominio.herramientas import Calculadora
from dominio.sorpresas import IMAGEN_ALONSO, respuesta_sorpresa
from dominio.modelos import ModeloReglas
from servicios.agente import Agente


class PruebaSorpresas(unittest.TestCase):
    def test_67_ya_no_activa_ninguna_sorpresa(self):
        for texto in ("67", " 67 ", "6 7", "Six Seven", "seis siete"):
            self.assertIsNone(respuesta_sorpresa(texto), texto)

    def test_alonso_con_cualquier_mezcla_de_mayusculas_y_dentro_de_una_frase(self):
        for texto in ("Fernando Alonso", "fERNANDO aLONSO", "FERNANDO   ALONSO", "fernando alonso!",
                      "Hola, Fernando Alonso ganó", "viva fernando alonso"):
            self.assertEqual(respuesta_sorpresa(texto), IMAGEN_ALONSO, texto)

    def test_no_se_activa_con_textos_normales_ni_dentro_de_otras_palabras(self):
        for texto in ("fernandoalonso", "fernando alonsos", "mifernando alonso", "alonso", "fernando",
                      "convierte 67 USD a euros", "2 + 67", "qué hora es?", ""):
            self.assertIsNone(respuesta_sorpresa(texto), texto)

    def test_la_imagen_apunta_a_una_ruta_publica_de_sorpresas(self):
        self.assertEqual(IMAGEN_ALONSO, "[[imagen:/sorpresas/fernando-alonso.jpg]]")

    def test_el_agente_responde_la_sorpresa_y_no_dice_que_no_entiende(self):
        agente = Agente(ModeloReglas(), [Calculadora()])
        self.assertEqual(agente.procesar("Fernando Alonso"), IMAGEN_ALONSO)
        self.assertNotIn("No estoy seguro", " ".join(m.contenido for m in agente.conversacion.get_mensajes()))
        self.assertEqual(agente.llamadas_realizadas, [])

    def test_un_67_dentro_de_una_cuenta_sigue_siendo_una_cuenta(self):
        agente = Agente(ModeloReglas(), [Calculadora()])
        self.assertIn("= 69", agente.procesar("2 + 67"))


if __name__ == "__main__":
    unittest.main()
