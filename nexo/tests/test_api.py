"""Tests de la API web: HTTP real sobre la app (TestClient), sin red ni modelos de pago."""

import json
import os
import tempfile
import unittest
from unittest import mock
from pathlib import Path

try:
    from fastapi.testclient import TestClient
except ImportError:  # la consola no necesita FastAPI: estos tests solo aplican a la web
    raise unittest.SkipTest("FastAPI no está instalado (pip install -r requirements-dev.txt)")

from dominio.excepciones import ErrorPersistencia
from main_web import construir_gestor
from presentacion.api import crear_app


def eventos_sse(texto: str) -> list[tuple[str, dict]]:
    resultado = []
    for bloque in texto.strip().split("\n\n"):
        lineas = dict(linea.split(": ", 1) for linea in bloque.splitlines())
        resultado.append((lineas["event"], json.loads(lineas["data"])))
    return resultado


class PruebaApi(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.gestor = construir_gestor(Path(self._tmp.name))
        self.cliente = TestClient(crear_app(self.gestor), raise_server_exceptions=False)

    def nueva(self) -> str:
        return self.cliente.post("/api/conversaciones").json()["id"]

    def enviar(self, id_conv: str, texto: str):
        return self.cliente.post(f"/api/conversaciones/{id_conv}/mensajes", json={"texto": texto})

    # --- información ---------------------------------------------------------
    def test_salud_modelos_y_herramientas(self):
        self.assertEqual(self.cliente.get("/api/salud").json(), {"estado": "ok"})
        self.assertTrue({"reglas", "eco"} <= {m["id"] for m in self.cliente.get("/api/modelos").json()})
        nombres = {h["nombre"] for h in self.cliente.get("/api/herramientas").json()}
        self.assertEqual(nombres, {"calculadora", "conversor_moneda", "buscador_faq", "consulta_stock", "reloj"})

    def test_catalogo_de_modelos_sin_clave(self):
        with mock.patch.dict(os.environ, {"LLM_API_KEY": ""}):
            with tempfile.TemporaryDirectory() as tmp:
                cliente = TestClient(crear_app(construir_gestor(Path(tmp))), raise_server_exceptions=False)
                modelos = cliente.get("/api/modelos").json()
                self.assertEqual([m["id"] for m in modelos], ["reglas", "eco", "llm"])
                self.assertEqual([m["tipo"] for m in modelos], ["local", "local", "remoto"])
                self.assertEqual(modelos[0]["nombre"], "ModeloReglas")
                self.assertEqual(
                    modelos[2],
                    {"id": "llm", "nombre": "ModeloLLM", "tipo": "remoto", "disponible": False,
                     "motivo": "Configura LLM_API_KEY en el archivo .env del servidor.", "detalle": None},
                )
                id_conv = cliente.post("/api/conversaciones").json()["id"]
                r = cliente.patch(f"/api/conversaciones/{id_conv}", json={"modelo": "llm"})
                self.assertEqual((r.status_code, r.json()["error"]["codigo"]), (422, "modelo_no_disponible"))
                self.assertIn("Configura LLM_API_KEY", r.json()["error"]["mensaje"])

    def test_catalogo_de_modelos_con_clave_no_la_filtra(self):
        with mock.patch.dict(os.environ, {"LLM_API_KEY": "clave-falsa-123", "LLM_MODEL": "gpt-4o"}):
            with tempfile.TemporaryDirectory() as tmp:
                gestor = construir_gestor(Path(tmp))
                self.addCleanup(lambda: [m.cerrar() for m in gestor.modelos.values() if hasattr(m, "cerrar")])
                cliente = TestClient(crear_app(gestor), raise_server_exceptions=False)
                r = cliente.get("/api/modelos")
                modelos = r.json()
                self.assertEqual([m["id"] for m in modelos], ["reglas", "eco", "llm"])
                self.assertEqual(
                    modelos[2],
                    {"id": "llm", "nombre": "ModeloLLM", "tipo": "remoto", "disponible": True,
                     "motivo": None, "detalle": "gpt-4o"},
                )
                self.assertNotIn("clave-falsa-123", r.text)

    # --- conversación y mensajes -----------------------------------------------------
    def test_mensaje_usa_herramienta_y_guarda_en_disco(self):
        id_conv = self.nueva()
        r = self.enviar(id_conv, "si compro 3 * 79.9 cuánto pago?")
        self.assertEqual(r.status_code, 200)
        cuerpo = r.json()
        self.assertIn("239.7", cuerpo["respuesta"])
        self.assertEqual(cuerpo["herramientas_usadas"][0]["nombre"], "calculadora")
        self.assertTrue((Path(self._tmp.name) / "conversaciones" / f"{id_conv}.json").exists())

    def test_encadenado_conversor_y_calculadora(self):
        id_conv = self.nueva()
        cuerpo = self.enviar(id_conv, "convierte 100 USD a euros y multiplícalo por 3").json()
        self.assertEqual([h["nombre"] for h in cuerpo["herramientas_usadas"]], ["conversor_moneda", "calculadora"])
        self.assertIn("276", cuerpo["respuesta"])

    def test_la_conversacion_se_recupera_de_disco_en_otro_gestor(self):
        id_conv = self.nueva()
        self.enviar(id_conv, "hola")
        otro = TestClient(crear_app(construir_gestor(Path(self._tmp.name))))
        estado = otro.get(f"/api/conversaciones/{id_conv}").json()
        self.assertEqual([m["rol"] for m in estado["mensajes"]], ["usuario", "asistente"])
        self.assertEqual(self.cliente.get("/api/conversaciones").json()[0]["id"], id_conv)

    def test_conversacion_vacia_no_se_guarda_hasta_el_primer_mensaje(self):
        self.nueva()
        self.assertEqual(self.cliente.get("/api/conversaciones").json(), [])

    def test_cambio_de_modelo_afecta_a_la_respuesta(self):
        id_conv = self.nueva()
        r = self.cliente.patch(f"/api/conversaciones/{id_conv}", json={"modelo": "eco"})
        self.assertEqual(r.json()["modelo"], "eco")
        self.assertEqual(self.enviar(id_conv, "hola").json()["respuesta"], "Has dicho: hola")

    # --- validación y errores -----------------------------------------------------------
    def test_mensaje_vacio_o_en_blanco_es_422(self):
        id_conv = self.nueva()
        for texto in ("", "   "):
            r = self.enviar(id_conv, texto)
            self.assertEqual(r.status_code, 422)
            self.assertEqual(r.json()["error"]["codigo"], "peticion_invalida")

    def test_mensaje_demasiado_largo_y_campos_extra_son_422(self):
        id_conv = self.nueva()
        self.assertEqual(self.enviar(id_conv, "a" * 2001).status_code, 422)
        r = self.cliente.post(f"/api/conversaciones/{id_conv}/mensajes", json={"texto": "hola", "modelo": "x"})
        self.assertEqual(r.status_code, 422)

    def test_modelo_inexistente_es_422(self):
        id_conv = self.nueva()
        r = self.cliente.patch(f"/api/conversaciones/{id_conv}", json={"modelo": "gpt-99"})
        self.assertEqual((r.status_code, r.json()["error"]["codigo"]), (422, "modelo_no_disponible"))

    def test_conversacion_inexistente_o_con_id_peligroso_es_404(self):
        r = self.cliente.get("/api/conversaciones/noexiste")
        self.assertEqual((r.status_code, r.json()["error"]["codigo"]), (404, "conversacion_no_encontrada"))
        r = self.cliente.get("/api/conversaciones/..%2Fsecreto")  # no sale de la carpeta de datos
        self.assertEqual((r.status_code, "error" in r.json()), (404, True))
        r = self.cliente.get("/api/conversaciones/a.b")
        self.assertEqual((r.status_code, r.json()["error"]["codigo"]), (404, "conversacion_no_encontrada"))
        r = self.cliente.post("/api/conversaciones/noexiste/mensajes", json={"texto": "hola"})
        self.assertEqual(r.status_code, 404)

    def test_limite_de_contexto_es_409_y_no_rompe_la_conversacion(self):
        id_conv = self.nueva()
        r = self.enviar(id_conv, "a " * 400)  # 400 palabras > 500 tokens
        self.assertEqual((r.status_code, r.json()["error"]["codigo"]), (409, "limite_contexto"))
        self.assertEqual(self.enviar(id_conv, "hola").status_code, 200)

    def test_error_de_almacenamiento_no_filtra_rutas(self):
        id_conv = self.nueva()
        def fallar(_):
            raise ErrorPersistencia(f"No se pudo guardar en {self._tmp.name}/secreto")
        self.gestor.guardar = fallar
        r = self.enviar(id_conv, "hola")
        self.assertEqual(r.status_code, 500)
        self.assertNotIn(self._tmp.name, r.text)

    def test_error_inesperado_devuelve_500_generico(self):
        id_conv = self.nueva()
        def romper(_):
            raise RuntimeError("detalle interno /etc/passwd")
        self.gestor.obtener(id_conv).procesar = romper
        r = self.enviar(id_conv, "hola")
        self.assertEqual((r.status_code, r.json()["error"]["codigo"]), (500, "error_interno"))
        self.assertNotIn("passwd", r.text)

    # --- streaming ---------------------------------------------------------------------------
    def test_stream_emite_herramienta_fragmentos_y_fin(self):
        id_conv = self.nueva()
        r = self.cliente.post(f"/api/conversaciones/{id_conv}/mensajes/stream", json={"texto": "cuánto tarda el envío?"})
        self.assertEqual(r.headers["content-type"].split(";")[0], "text/event-stream")
        eventos = eventos_sse(r.text)
        tipos = [e for e, _ in eventos]
        self.assertEqual(tipos[0], "herramienta")
        self.assertEqual(tipos[-1], "fin")
        self.assertGreater(tipos.count("fragmento"), 1)
        texto = "".join(d["texto"] for e, d in eventos if e == "fragmento")
        self.assertEqual(texto, eventos[-1][1]["mensajes"][-1]["contenido"])  # coincide con lo guardado

    def test_stream_error_viaja_como_evento(self):
        id_conv = self.nueva()
        r = self.cliente.post(f"/api/conversaciones/{id_conv}/mensajes/stream", json={"texto": "a " * 400})
        self.assertEqual(eventos_sse(r.text), [("error", {"codigo": "limite_contexto", "mensaje": eventos_sse(r.text)[0][1]["mensaje"]})])

    def test_stream_de_conversacion_inexistente_es_404_normal(self):
        r = self.cliente.post("/api/conversaciones/noexiste/mensajes/stream", json={"texto": "hola"})
        self.assertEqual(r.status_code, 404)

    # --- estadísticas -------------------------------------------------------------------------
    def test_estadisticas_proceden_de_datos_reales(self):
        vacias = self.cliente.get("/api/estadisticas").json()
        self.assertEqual((vacias["peticiones"], vacias["herramientas"]), (0, {}))
        id_conv = self.nueva()
        self.enviar(id_conv, "2 + 2")
        self.enviar(id_conv, "2 / 0")
        stats = self.cliente.get("/api/estadisticas").json()
        self.assertEqual(stats["peticiones"], 2)
        self.assertEqual(stats["herramientas"]["calculadora"], {"usos": 2, "fallos": 1})
        self.assertGreater(stats["tokens_entrada_estimados"], 0)
        self.assertGreater(stats["tokens_salida_estimados"], 0)
        self.assertEqual(stats["tokens_salida_llm"], 0)


if __name__ == "__main__":
    unittest.main()
