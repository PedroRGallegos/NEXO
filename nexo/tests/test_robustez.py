"""Regresiones encontradas al intentar romper el programa (sin FastAPI)."""

import json
import tempfile
import unittest
from pathlib import Path

from dominio.excepciones import ConversacionNoEncontrada, ErrorPersistencia
from dominio.mensaje import Conversacion
from persistencia.registro_uso import RegistroUso
from persistencia.repositorio_conversaciones import RepositorioConversaciones
from servicios.gestor_conversaciones import resumir


class PruebaRepositorioRobusto(unittest.TestCase):
    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp())
        self.repo = RepositorioConversaciones(self.carpeta)

    def test_id_demasiado_largo_es_no_encontrado_y_no_error_del_sistema_de_ficheros(self):
        with self.assertRaises(ConversacionNoEncontrada):
            self.repo.cargar("a" * 300)

    def test_json_anidado_en_exceso_se_trata_como_fichero_danado(self):
        (self.carpeta / "hondo.json").write_text("[" * 100_000, encoding="utf-8")
        with self.assertRaises(ErrorPersistencia):
            self.repo.cargar("hondo")

    def test_fecha_con_tipo_raro_no_rompe_el_resumen(self):
        conversacion = Conversacion.from_dict(
            {"id": "x1", "limite_tokens": 500, "mensajes": [{"rol": "usuario", "contenido": "hola", "fecha": 123}]}
        )
        self.assertIsInstance(resumir(conversacion)["actualizada"], str)


class PruebaRegistroUsoRobusto(unittest.TestCase):
    def registro_con_fila(self, fila):
        ruta = Path(tempfile.mkdtemp()) / "uso.csv"
        registro = RegistroUso(ruta)
        registro.registrar_llm("pregunta", 10, 0.5)
        with ruta.open("a", encoding="utf-8") as fichero:
            fichero.write(fila + "\n")
        return registro

    def test_una_fila_danada_no_tumba_las_estadisticas(self):
        for fila in ("2026,preg,,0.1,,,,,", "2026,preg,abc,0.1,,,,,", "2026,preg,5,nan,,,,,", "2026,preg,5,1e999,,,,,"):
            with self.subTest(fila=fila):
                resumen = self.registro_con_fila(fila).resumen_llm()
                self.assertEqual(resumen, {"output_tokens": 10, "cost": 0.5})


if __name__ == "__main__":
    unittest.main()
