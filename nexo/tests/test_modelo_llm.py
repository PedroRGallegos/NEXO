"""Pruebas del modelo remoto sin llamadas de red ni claves reales."""

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from tenacity import wait_none

from dominio.herramientas import Calculadora
from dominio.excepciones import ErrorProveedorLLM
from dominio.mensaje import Conversacion, Mensaje
from dominio.modelos import ModeloLLM, PeticionInvalida, validar
from persistencia.registro_uso import RegistroUso
from persistencia.repositorio_conversaciones import RepositorioConversaciones
from presentacion.api import crear_app
from servicios.agente import Agente
from servicios.gestor_conversaciones import GestorConversaciones


def respuesta_sse(texto="Hola", tokens=12):
    eventos = [
        {"choices": [{"delta": {"content": texto}}]},
        {"choices": [], "usage": {"completion_tokens": tokens}},
    ]
    return "".join(f"data: {json.dumps(evento)}\n\n" for evento in eventos) + "data: [DONE]\n\n"


class TestValidacionLLM(unittest.TestCase):
    def test_rechaza_historial_vacio_o_primer_rol_incorrecto(self):
        for mensajes in ([], [{"role": "assistant", "content": "Hola"}]):
            with self.subTest(mensajes=mensajes), self.assertRaises(PeticionInvalida):
                validar(mensajes, 150, 0.7)

    def test_rechaza_roles_y_parametros_invalidos(self):
        casos = [
            ([{"role": "developer", "content": "x"}], 150, 0.7),
            ([{"role": "user", "content": "x"}], 0, 0.7),
            ([{"role": "user", "content": "x"}], -1, 0.7),
            ([{"role": "user", "content": "x"}], 150, -0.1),
            ([{"role": "user", "content": "x"}], 150, 2.1),
        ]
        for mensajes, max_tokens, temperature in casos:
            with self.subTest(max_tokens=max_tokens, temperature=temperature), self.assertRaises(PeticionInvalida):
                validar(mensajes, max_tokens, temperature)

    def test_acepta_limites_inclusivos_de_temperature(self):
        mensaje = [{"role": "user", "content": "Hola"}]
        validar(mensaje, 1, 0)
        validar(mensaje, 1, 2)


class TestModeloLLM(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.registro = RegistroUso(Path(self.temporal.name) / "uso.csv")

    def modelo(self, manejador, **opciones):
        cliente = httpx.Client(transport=httpx.MockTransport(manejador))
        self.addCleanup(cliente.close)
        # Valores explícitos: las pruebas no deben depender del .env de quien las ejecute.
        parametros = dict(
            nombre="modelo-prueba",
            api_key="clave-falsa",
            api_url="https://llm.test/chat/completions",
            max_tokens=150,
            temperature=0.7,
            coste_por_1000_tokens=0.008,
            max_tokens_ampliado=0,
            instruccion="",
            esfuerzo_razonamiento="",
            registrar_uso=self.registro.registrar_llm,
            cliente=cliente,
        )
        parametros.update(opciones)
        return ModeloLLM(**parametros)

    def conversacion(self):
        conversacion = Conversacion()
        conversacion.agregar(Mensaje("usuario", "¿Qué puedes hacer?"))
        return conversacion

    def test_transmite_fragmentos_y_registra_tokens_coste_y_pregunta(self):
        def responder(request):
            cuerpo = json.loads(request.read())
            self.assertTrue(cuerpo["stream"])
            self.assertEqual(cuerpo["max_tokens"], 150)
            self.assertEqual(request.headers["Authorization"], "Bearer clave-falsa")
            return httpx.Response(200, text=respuesta_sse("Hola NEXO", 12))

        modelo = self.modelo(responder)
        eventos = list(modelo.responder_por_fragmentos(self.conversacion(), []))
        self.assertEqual([e["tipo"] for e in eventos], ["fragmento", "respuesta"])
        self.assertEqual(eventos[-1]["respuesta"].texto, "Hola NEXO")
        with (Path(self.temporal.name) / "uso.csv").open(newline="", encoding="utf-8") as fichero:
            fila = next(csv.DictReader(fichero))
        self.assertEqual(fila["question"], "¿Qué puedes hacer?")
        self.assertEqual(int(fila["output_tokens"]), 12)
        self.assertAlmostEqual(float(fila["cost"]), (12 * 0.008) / 1000)

    def test_reintenta_429_hasta_que_el_proveedor_responde(self):
        intentos = 0

        def responder(_):
            nonlocal intentos
            intentos += 1
            if intentos < 3:
                return httpx.Response(429)
            return httpx.Response(200, text=respuesta_sse())

        modelo = self.modelo(responder)
        with patch.object(modelo._abrir_stream.retry, "wait", wait_none()):
            respuesta = modelo.responder(self.conversacion(), [])
        self.assertEqual(respuesta.texto, "Hola")
        self.assertEqual(intentos, 3)

    def test_reintenta_respuestas_5xx(self):
        intentos = 0

        def responder(_):
            nonlocal intentos
            intentos += 1
            if intentos == 1:
                return httpx.Response(503)
            return httpx.Response(200, text=respuesta_sse())

        modelo = self.modelo(responder)
        with patch.object(modelo._abrir_stream.retry, "wait", wait_none()):
            respuesta = modelo.responder(self.conversacion(), [])
        self.assertEqual(respuesta.texto, "Hola")
        self.assertEqual(intentos, 2)

    def test_detiene_los_reintentos_tras_cinco_errores_transitorios(self):
        intentos = 0

        def responder(_):
            nonlocal intentos
            intentos += 1
            return httpx.Response(429)

        modelo = self.modelo(responder)
        with patch.object(modelo._abrir_stream.retry, "wait", wait_none()):
            with self.assertRaises(ErrorProveedorLLM):
                modelo.responder(self.conversacion(), [])
        self.assertEqual(intentos, 5)

    def test_no_reintenta_errores_http_no_transitorios(self):
        intentos = 0

        def responder(_):
            nonlocal intentos
            intentos += 1
            return httpx.Response(400)

        modelo = self.modelo(responder)
        with self.assertRaises(ErrorProveedorLLM), patch.object(
            modelo._abrir_stream.retry, "wait", wait_none()
        ):
            modelo.responder(self.conversacion(), [])
        self.assertEqual(intentos, 1)

    def test_agente_puede_recibir_fragmentos_de_una_respuesta(self):
        modelo = self.modelo(lambda _: httpx.Response(200, text=respuesta_sse("En tiempo real", 4)))
        agente = Agente(modelo, [])
        eventos = list(agente.procesar_por_pasos("Pregunta de prueba"))
        self.assertEqual([evento["tipo"] for evento in eventos], ["fragmento", "final"])
        self.assertEqual(eventos[0]["texto"], "En tiempo real")
        self.assertTrue(eventos[-1]["fragmentada"])

    def test_api_transmite_fragmentos_llm_sin_volver_a_dividirlos(self):
        modelo = self.modelo(lambda _: httpx.Response(200, text=respuesta_sse("Hola NEXO", 12)))
        gestor = GestorConversaciones(
            lambda: Agente(modelo, [], self.registro),
            RepositorioConversaciones(Path(self.temporal.name) / "conversaciones"),
            {"llm": modelo},
        )
        with TestClient(crear_app(gestor)) as cliente:
            id_conv = cliente.post("/api/conversaciones").json()["id"]
            flujo = cliente.post(
                f"/api/conversaciones/{id_conv}/mensajes/stream",
                json={"texto": "Pregunta de prueba"},
            )
            estadisticas = cliente.get("/api/estadisticas").json()
        eventos = []
        for bloque in flujo.text.strip().split("\n\n"):
            lineas = dict(linea.split(": ", 1) for linea in bloque.splitlines())
            eventos.append((lineas["event"], json.loads(lineas["data"])))
        self.assertEqual([tipo for tipo, _ in eventos], ["fragmento", "fin"])
        self.assertEqual(eventos[0][1]["texto"], "Hola NEXO")
        self.assertEqual(eventos[1][1]["mensajes"][-1]["contenido"], "Hola NEXO")
        self.assertEqual(self.registro.resumen_llm()["output_tokens"], 12)
        self.assertEqual(estadisticas["tokens_salida_llm"], 12)
        self.assertAlmostEqual(estadisticas["coste_eur"], (12 * 0.008) / 1000)

    def test_llm_puede_solicitar_una_herramienta_al_agente(self):
        intentos = 0

        def responder(request):
            nonlocal intentos
            intentos += 1
            cuerpo = json.loads(request.read())
            if intentos == 1:
                self.assertEqual(cuerpo["tools"][0]["function"]["name"], "calculadora")
                llamada = {
                    "choices": [{
                        "delta": {
                            "tool_calls": [{
                                "index": 0,
                                "function": {
                                    "name": "calculadora",
                                    "arguments": '{"a": 2, "b": 2, "operacion": "+"}',
                                },
                            }],
                        },
                    }],
                }
                uso = {"choices": [], "usage": {"completion_tokens": 8}}
                return httpx.Response(200, text="".join(
                    f"data: {json.dumps(evento)}\n\n" for evento in (llamada, uso)
                ))
            self.assertIn("Resultado de herramienta", cuerpo["messages"][-1]["content"])
            return httpx.Response(200, text=respuesta_sse("2 + 2 = 4", 10))

        modelo = self.modelo(responder)
        agente = Agente(modelo, [Calculadora()])
        eventos = list(agente.procesar_por_pasos("¿Cuánto es 2 + 2?"))
        self.assertEqual([evento["tipo"] for evento in eventos], ["herramienta", "fragmento", "final"])
        self.assertEqual(eventos[0]["nombre"], "calculadora")
        self.assertEqual(eventos[-1]["texto"], "2 + 2 = 4")
        self.assertEqual(intentos, 2)


if __name__ == "__main__":
    unittest.main()
