"""Tests de la capa de dominio (no hay input() ni print(), así que se pueden probar sin más)."""

import unittest

from dominio.excepciones import ArgumentosInvalidos, LimiteContextoSuperado
from dominio.herramientas import BuscadorFAQ, Calculadora, ConversorMoneda, Herramienta
from dominio.mensaje import Conversacion, Mensaje
from dominio.modelos import Modelo, ModeloEco, ModeloReglas


def conversacion_con(texto, rol="usuario"):
    conversacion = Conversacion()
    conversacion.agregar(Mensaje(rol, texto))
    return conversacion


class TestMensaje(unittest.TestCase):
    def test_rol_invalido(self):
        with self.assertRaises(ValueError):
            Mensaje("robot", "hola")

    def test_str_y_to_dict(self):
        mensaje = Mensaje("usuario", "Hola", "2026-10-20T10:15:00")
        self.assertEqual(str(mensaje), "[usuario] Hola")
        self.assertEqual(
            mensaje.to_dict(),
            {"rol": "usuario", "contenido": "Hola", "fecha": "2026-10-20T10:15:00"},
        )

    def test_ida_y_vuelta(self):
        original = Mensaje("asistente", "Hola")
        self.assertEqual(Mensaje.from_dict(original.to_dict()).to_dict(), original.to_dict())

    def test_atributos_solo_lectura(self):
        with self.assertRaises(AttributeError):
            Mensaje("usuario", "x").rol = "asistente"

    def test_desglosar_herramienta(self):
        self.assertEqual(
            Mensaje.de_herramienta("calculadora", "3 * 4 = 12").desglosar_herramienta(),
            ("calculadora", "3 * 4 = 12", False),
        )
        self.assertEqual(
            Mensaje.de_herramienta("calculadora", "fallo", error=True).desglosar_herramienta(),
            ("calculadora", "fallo", True),
        )


class TestConversacion(unittest.TestCase):
    def test_get_mensajes_devuelve_copia(self):
        conversacion = conversacion_con("hola")
        conversacion.get_mensajes().clear()
        self.assertEqual(len(conversacion), 1)

    def test_mensajes_es_privado(self):
        self.assertFalse(hasattr(Conversacion(), "mensajes"))
        self.assertFalse(hasattr(Conversacion(), "__mensajes"))

    def test_tokens_estimados(self):
        # 10 palabras * 1,3 = 13
        self.assertEqual(conversacion_con("uno dos tres cuatro cinco seis siete ocho nueve diez").tokens_estimados(), 13)

    def test_limite_de_tokens(self):
        conversacion = Conversacion(limite_tokens=10)
        conversacion.agregar(Mensaje("usuario", "uno dos tres"))  # 4 tokens
        with self.assertRaises(LimiteContextoSuperado):
            conversacion.agregar(Mensaje("usuario", "a b c d e f g h"))
        self.assertEqual(len(conversacion), 1)  # el mensaje rechazado no se añade

    def test_ida_y_vuelta(self):
        conversacion = conversacion_con("hola")
        copia = Conversacion.from_dict(conversacion.to_dict())
        self.assertEqual(copia.to_dict(), conversacion.to_dict())


class TestHerramientas(unittest.TestCase):
    def test_base_no_implementada(self):
        with self.assertRaises(NotImplementedError):
            Herramienta("x", "y").ejecutar()

    def test_calculadora(self):
        calculadora = Calculadora()
        self.assertEqual(calculadora.ejecutar(a=3, b=4, operacion="*"), "3 * 4 = 12")
        self.assertEqual(calculadora.ejecutar(a=3, b=79.9, operacion="*"), "3 * 79.9 = 239.7")
        self.assertEqual(calculadora.ejecutar(a=10, b=4, operacion="/"), "10 / 4 = 2.5")
        self.assertEqual(calculadora.ejecutar(a=1, b=2, operacion="-"), "1 - 2 = -1")

    def test_calculadora_errores(self):
        calculadora = Calculadora()
        for argumentos in (
            {"a": 1, "b": 0, "operacion": "/"},
            {"a": 1, "b": 2, "operacion": "^"},
            {"a": "hola", "b": 2, "operacion": "+"},
            {"a": 1},
        ):
            with self.subTest(argumentos=argumentos), self.assertRaises(ArgumentosInvalidos):
                calculadora.ejecutar(**argumentos)

    def test_conversor(self):
        conversor = ConversorMoneda()
        self.assertEqual(conversor.ejecutar(cantidad=250, origen="USD", destino="EUR"), "250 USD = 230.00 EUR")
        self.assertEqual(conversor.ejecutar(cantidad=100, origen="eur", destino="gbp"), "100 EUR = 85.47 GBP")

    def test_conversor_errores(self):
        with self.assertRaises(ArgumentosInvalidos):
            ConversorMoneda().ejecutar(cantidad=1, origen="XXX", destino="EUR")
        with self.assertRaises(ArgumentosInvalidos):
            ConversorMoneda().ejecutar(cantidad=-5, origen="USD", destino="EUR")

    def test_buscador_faq(self):
        buscador = BuscadorFAQ()
        self.assertIn("24-48 h", buscador.ejecutar(pregunta="¿Cuánto tarda el envío?"))
        self.assertIn("Bizum", buscador.ejecutar(pregunta="puedo pagar con tarjeta"))
        self.assertEqual(buscador.ejecutar(pregunta="blablabla"), "No encontrado")

    def test_polimorfismo_str(self):
        self.assertTrue(str(Calculadora()).startswith("🔧 calculadora:"))


class TestModelos(unittest.TestCase):
    def test_base_no_implementada(self):
        with self.assertRaises(NotImplementedError):
            Modelo("x").responder(Conversacion(), [])

    def test_eco(self):
        respuesta = ModeloEco().responder(conversacion_con("hola"), [])
        self.assertEqual(respuesta.texto, "Has dicho: hola")
        self.assertFalse(respuesta.es_llamada_herramienta())

    def test_reglas_calculadora(self):
        respuesta = ModeloReglas().responder(conversacion_con("si compro 3 * 79,9 cuánto pago?"), [])
        self.assertEqual(respuesta.herramienta, "calculadora")
        self.assertEqual(respuesta.argumentos, {"a": 3, "b": 79.9, "operacion": "*"})

    def test_reglas_x_como_multiplicacion(self):
        respuesta = ModeloReglas().responder(conversacion_con("3 x 4"), [])
        self.assertEqual(respuesta.argumentos["operacion"], "*")

    def test_reglas_conversor(self):
        respuesta = ModeloReglas().responder(conversacion_con("cuánto son 250 USD en euros"), [])
        self.assertEqual(respuesta.herramienta, "conversor_moneda")
        self.assertEqual(respuesta.argumentos, {"cantidad": 250, "origen": "USD", "destino": "EUR"})
        respuesta = ModeloReglas().responder(conversacion_con("100 euros en dólares"), [])
        self.assertEqual(respuesta.argumentos, {"cantidad": 100, "origen": "EUR", "destino": "USD"})

    def test_reglas_conversor_sin_cantidad(self):
        respuesta = ModeloReglas().responder(conversacion_con("pasa a dólares"), [])
        self.assertFalse(respuesta.es_llamada_herramienta())

    def test_reglas_faq(self):
        for frase in ("cuánto tarda el envío?", "puedo devolver algo", "¿cuál es el horario?", "formas de pago"):
            with self.subTest(frase=frase):
                self.assertEqual(ModeloReglas().responder(conversacion_con(frase), []).herramienta, "buscador_faq")

    def test_reglas_saludo_y_desconocido(self):
        self.assertEqual(
            ModeloReglas().responder(conversacion_con("hola"), []).texto, "¡Hola! Soy NEXO, ¿en qué te ayudo?"
        )
        self.assertEqual(
            ModeloReglas().responder(conversacion_con("quiero un yate"), []).texto,
            "No estoy seguro, ¿puedes reformularlo?",
        )

    def test_reglas_tras_herramienta(self):
        conversacion = conversacion_con("")  # mensaje de usuario previo
        conversacion.agregar(Mensaje.de_herramienta("calculadora", "3 * 4 = 12"))
        respuesta = ModeloReglas().responder(conversacion, [])
        self.assertEqual(respuesta.texto, "El resultado es 3 * 4 = 12. ¿Necesitas algo más?")


if __name__ == "__main__":
    unittest.main()
