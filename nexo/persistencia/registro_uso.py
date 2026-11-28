"""Registro de uso de herramientas en un CSV (observabilidad básica del agente)."""

import csv
import math
from datetime import datetime
from pathlib import Path
from threading import Lock

from dominio.excepciones import ErrorPersistencia


class RegistroUso:
    """Añade una fila a ``uso.csv`` cada vez que se ejecuta una herramienta."""

    CAMPOS = (
        "timestamp",
        "question",
        "output_tokens",
        "cost",
        "fecha",
        "herramienta",
        "argumentos",
        "exito",
        "milisegundos",
    )
    CAMPOS_ANTERIORES = ("fecha", "herramienta", "argumentos", "exito", "milisegundos")

    def __init__(self, ruta="datos/uso.csv"):
        self._ruta = Path(ruta)
        self._lock = Lock()
        try:
            self._ruta.parent.mkdir(parents=True, exist_ok=True)
            self._preparar_archivo()
        except OSError as error:
            raise ErrorPersistencia(f"No se puede preparar el registro de uso: {error}") from error

    def registrar(self, herramienta: str, argumentos: dict, exito: bool, milisegundos: float) -> None:
        ahora = datetime.now().isoformat(timespec="seconds")
        fila = {
            "timestamp": "",
            "question": "",
            "output_tokens": "",
            "cost": "",
            "fecha": ahora,
            "herramienta": herramienta,
            "argumentos": str(argumentos),
            "exito": bool(exito),
            "milisegundos": round(milisegundos, 2),
        }
        try:
            self._anexar(fila)
        except OSError as error:
            raise ErrorPersistencia(f"No se pudo escribir en el registro de uso: {error}") from error

    def registrar_llm(self, pregunta: str, tokens_salida: int, coste: float) -> None:
        fila = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "question": pregunta,
            "output_tokens": tokens_salida,
            "cost": f"{coste:.6f}",
            "fecha": "",
            "herramienta": "",
            "argumentos": "",
            "exito": "",
            "milisegundos": "",
        }
        try:
            self._anexar(fila)
        except OSError as error:
            raise ErrorPersistencia(f"No se pudo escribir el uso del modelo: {error}") from error

    def _preparar_archivo(self) -> None:
        if not self._ruta.exists() or self._ruta.stat().st_size == 0:
            with self._ruta.open("w", newline="", encoding="utf-8") as fichero:
                csv.DictWriter(fichero, fieldnames=self.CAMPOS).writeheader()
            return

        with self._ruta.open("r", newline="", encoding="utf-8") as fichero:
            lector = csv.DictReader(fichero)
            campos = tuple(lector.fieldnames or ())
            filas = list(lector)
        if campos == self.CAMPOS:
            return
        if campos != self.CAMPOS_ANTERIORES:
            raise ErrorPersistencia("El registro de uso tiene una cabecera CSV no reconocida.")

        filas_nuevas = []
        for fila in filas:
            filas_nuevas.append({
                "timestamp": "",
                "question": "",
                "output_tokens": "",
                "cost": "",
                **fila,
            })
        temporal = self._ruta.with_suffix(self._ruta.suffix + ".tmp")
        with temporal.open("w", newline="", encoding="utf-8") as fichero:
            escritor = csv.DictWriter(fichero, fieldnames=self.CAMPOS)
            escritor.writeheader()
            escritor.writerows(filas_nuevas)
        temporal.replace(self._ruta)

    def _anexar(self, fila: dict) -> None:
        with self._lock, self._ruta.open("a", newline="", encoding="utf-8") as fichero:
            csv.DictWriter(fichero, fieldnames=self.CAMPOS).writerow(fila)

    def resumen(self) -> dict:
        """``{herramienta: {"usos": n, "fallos": m}}`` a partir del CSV."""
        resumen: dict[str, dict[str, int]] = {}
        if not self._ruta.exists():
            return resumen
        try:
            with self._ruta.open("r", newline="", encoding="utf-8") as fichero:
                for fila in csv.DictReader(fichero):
                    nombre = fila.get("herramienta")
                    if not nombre:
                        continue
                    datos = resumen.setdefault(nombre, {"usos": 0, "fallos": 0})
                    datos["usos"] += 1
                    if fila.get("exito") != "True":
                        datos["fallos"] += 1
        except (OSError, csv.Error) as error:
            raise ErrorPersistencia(f"No se pudo leer el registro de uso: {error}") from error
        return resumen

    def resumen_llm(self) -> dict:
        """Totales reales de tokens de salida y coste registrados para el LLM."""
        tokens_salida = 0
        coste = 0.0
        if not self._ruta.exists():
            return {"output_tokens": 0, "cost": 0.0}
        try:
            with self._ruta.open("r", newline="", encoding="utf-8") as fichero:
                for fila in csv.DictReader(fichero):
                    if not fila.get("question"):
                        continue
                    try:
                        tokens = int(fila["output_tokens"])
                        importe = float(fila["cost"])
                    except (KeyError, TypeError, ValueError, OverflowError):
                        continue  # una fila dañada no debe tumbar las estadísticas
                    if not math.isfinite(importe):
                        continue
                    tokens_salida += tokens
                    coste += importe
        except (OSError, csv.Error) as error:
            raise ErrorPersistencia(f"No se pudo leer el uso del modelo: {error}") from error
        return {"output_tokens": tokens_salida, "cost": round(coste, 6)}