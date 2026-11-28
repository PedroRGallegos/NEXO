"""ModeloLLM con respuestas al estilo Groq/OpenAI, sin red: cliente simulado (sin httpx real)."""

import json
import unittest

from dominio.mensaje import Conversacion, Mensaje
from dominio.modelos import ModeloLLM, _tokens_de_uso


class RespuestaFalsa:
    def __init__(self, fragmentos):
        self._lineas = [f"data: {json.dumps(f)}" for f in fragmentos] + ["data: [DONE]"]

    def raise_for_status(self):
        pass

    def iter_lines(self):
        return iter(self._lineas)

    def close(self):
        pass


class ClienteFalso:
    def __init__(self, fragmentos, siguientes=None):
        self.fragmentos = fragmentos
        self.siguientes = list(siguientes or [])
        self.peticiones = []

    def build_request(self, metodo, url, json=None, headers=None):
        self.peticiones.append({"url": url, "json": json, "headers": headers})
        return object()

    def send(self, solicitud, stream=False):
        if len(self.peticiones) > 1 and self.siguientes:
            return RespuestaFalsa(self.siguientes.pop(0))
        return RespuestaFalsa(self.fragmentos)

    def close(self):
        pass


def conversacion():
    c = Conversacion()
    c.agregar(Mensaje("usuario", "hola"))
    return c


def modelo(fragmentos, usos=None, siguientes=None, **extra):
    registro = [] if usos is None else usos
    m = ModeloLLM(
        nombre="llama-3.3-70b-versatile",
        api_key="gsk_prueba",
        api_url="https://api.groq.com/openai/v1/chat/completions",
        registrar_uso=lambda p, t, c: registro.append((p, t)),
        cliente=ClienteFalso(fragmentos, siguientes),
        # Valores explícitos: las pruebas no deben depender del .env de quien las ejecute.
        **{"max_tokens": 500, "temperature": 0.7, "coste_por_1000_tokens": 0.008,
           "max_tokens_ampliado": 0, "instruccion": "Responde en español.", "esfuerzo_razonamiento": "", **extra},
    )
    return m


class CompatibilidadProveedor(unittest.TestCase):
    def test_uso_en_x_groq_se_lee(self):
        self.assertEqual(_tokens_de_uso({"x_groq": {"usage": {"completion_tokens": 7}}}), 7)
        self.assertEqual(_tokens_de_uso({"usage": {"completion_tokens": 3}}), 3)
        self.assertIsNone(_tokens_de_uso({"choices": []}))

    def test_texto_con_uso_de_groq(self):
        usos = []
        m = modelo(
            [
                {"choices": [{"delta": {"content": "Hola"}}]},
                {"choices": [{"delta": {}}], "x_groq": {"usage": {"completion_tokens": 5}}},
            ],
            usos,
        )
        r = m.responder(conversacion(), [])
        self.assertEqual(r.texto, "Hola")
        self.assertEqual(usos, [("hola", 5)])
        envio = m._cliente.peticiones[0]
        self.assertEqual(envio["url"], "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(envio["headers"]["Authorization"], "Bearer gsk_prueba")

    def test_sin_uso_en_streaming_se_estima_en_vez_de_fallar(self):
        usos = []
        m = modelo([{"choices": [{"delta": {"content": "Hola, ¿qué tal estás hoy?"}}]}], usos)
        r = m.responder(conversacion(), [])
        self.assertEqual(r.texto, "Hola, ¿qué tal estás hoy?")
        self.assertEqual(len(usos), 1)
        self.assertGreaterEqual(usos[0][1], 1)

    def test_varias_herramientas_atiende_la_primera(self):
        m = modelo(
            [
                {"choices": [{"delta": {"tool_calls": [
                    {"index": 0, "function": {"name": "reloj", "arguments": "{}"}},
                    {"index": 1, "function": {"name": "calculadora", "arguments": "{}"}},
                ]}}]},
            ]
        )
        r = m.responder(conversacion(), [])
        self.assertEqual(r.herramienta, "reloj")


class LimiteAmpliado(unittest.TestCase):
    CORTADA = [
        {"choices": [{"delta": {"content": "Primera parte"}}]},
        {"choices": [{"delta": {}, "finish_reason": "length"}], "usage": {"completion_tokens": 500}},
    ]
    RESTO = [
        {"choices": [{"delta": {"content": " y segunda parte."}}]},
        {"choices": [{"delta": {}, "finish_reason": "stop"}], "usage": {"completion_tokens": 120}},
    ]

    def test_respuesta_cortada_se_continua_hasta_el_tope_ampliado(self):
        usos = []
        m = modelo(self.CORTADA, usos, siguientes=[self.RESTO], max_tokens_ampliado=1000)
        r = m.responder(conversacion(), [])
        self.assertEqual(r.texto, "Primera parte y segunda parte.")
        self.assertEqual(usos, [("hola", 620)])
        primera, segunda = m._cliente.peticiones
        self.assertEqual(primera["json"]["max_tokens"], 500)
        self.assertEqual(segunda["json"]["max_tokens"], 500)  # 1000 - 500 ya gastados
        self.assertEqual(segunda["json"]["messages"][-2]["role"], "assistant")

    def test_sin_tope_ampliado_no_hay_segunda_peticion(self):
        m = modelo(self.CORTADA, siguientes=[self.RESTO], max_tokens_ampliado=0)
        r = m.responder(conversacion(), [])
        self.assertEqual(r.texto, "Primera parte")
        self.assertEqual(len(m._cliente.peticiones), 1)

    def test_respuesta_completa_no_se_amplia(self):
        completa = [
            {"choices": [{"delta": {"content": "Listo"}}]},
            {"choices": [{"delta": {}, "finish_reason": "stop"}], "usage": {"completion_tokens": 3}},
        ]
        m = modelo(completa, siguientes=[self.RESTO], max_tokens_ampliado=1000)
        self.assertEqual(m.responder(conversacion(), []).texto, "Listo")
        self.assertEqual(len(m._cliente.peticiones), 1)

    def test_instruccion_y_esfuerzo_se_envian_solo_si_corresponde(self):
        m = modelo([{"choices": [{"delta": {"content": "ok"}}]}], esfuerzo_razonamiento="low")
        m.responder(conversacion(), [])
        cuerpo = m._cliente.peticiones[0]["json"]
        self.assertEqual(cuerpo["messages"][0]["role"], "system")
        self.assertEqual(cuerpo["reasoning_effort"], "low")
        sin = modelo([{"choices": [{"delta": {"content": "ok"}}]}], instruccion="")
        sin.responder(conversacion(), [])
        c2 = sin._cliente.peticiones[0]["json"]
        self.assertNotIn("reasoning_effort", c2)
        self.assertEqual(c2["messages"][0]["role"], "user")


if __name__ == "__main__":
    unittest.main()
