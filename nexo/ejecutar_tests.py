#!/usr/bin/env python3
"""Ejecuta TODOS los tests de NEXO con un solo comando y muestra un resumen.

Suites:
  * Python: cada fichero ``tests/test_*.py`` se lanza por separado con
    ``python -m unittest`` (mismo intérprete que este script). Así, si uno no
    puede importarse por falta de una dependencia (fastapi, httpx...), se marca
    OMITIDO con el motivo sin tumbar el resto.
  * Frontend: ``npm test`` (vitest) dentro de ``frontend/``.

Estados: OK (todo pasa), FALLO (algún test falla o la suite no termina),
OMITIDO (no se pudo ejecutar por falta de dependencias/herramientas).

Uso (desde cualquier carpeta):
    python ejecutar_tests.py [--solo-python | --solo-frontend] [-v] [--estricto]

Código de salida: 0 sin fallos; 1 con algún fallo (o con omitidas si --estricto);
130 si se interrumpe con Ctrl+C. Solo biblioteca estándar.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DIR_TESTS = RAIZ / "tests"
DIR_FRONTEND = RAIZ / "frontend"
TIMEOUT_S = 300  # por suite

OK, FALLO, OMITIDO = "OK", "FALLO", "OMITIDO"

# Paquetes propios del proyecto: un ModuleNotFoundError sobre ellos es un fallo
# real (código roto), no una dependencia externa que falta.
MODULOS_PROPIOS = {"dominio", "servicios", "persistencia", "presentacion",
                   "tests", "main", "main_web", "datos"}

RE_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


@dataclass
class Resultado:
    nombre: str
    estado: str = OK
    ejecutados: int | None = None
    pasados: int | None = None
    fallados: int | None = None
    duracion: float = 0.0
    motivo: str = ""                 # explicación para OMITIDO / FALLO
    salida: str = ""                 # salida completa (para -v)
    lineas_fallo: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
def ejecutar(cmd: list[str], cwd: Path, extra_env: dict[str, str] | None = None):
    """Lanza un proceso (sin shell) con timeout. Devuelve (codigo, salida, agotado)."""
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
           "PYTHONIOENCODING": "utf-8", "NO_COLOR": "1", "FORCE_COLOR": "0"}
    env.update(extra_env or {})
    kwargs: dict = {}
    if os.name == "posix":
        kwargs["start_new_session"] = True  # para poder matar todo el grupo
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, **kwargs)
    try:
        bruto, _ = proc.communicate(timeout=TIMEOUT_S)
        agotado = False
    except subprocess.TimeoutExpired:
        _matar(proc)
        bruto, _ = proc.communicate()
        agotado = True
    except KeyboardInterrupt:
        _matar(proc)
        raise
    texto = RE_ANSI.sub("", bruto.decode("utf-8", errors="replace"))
    return proc.returncode, texto, agotado


def _matar(proc: subprocess.Popen) -> None:
    """Termina el proceso y sus hijos (npm lanza node, que lanza vitest)."""
    try:
        if os.name == "posix":
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True)
    except (ProcessLookupError, OSError):
        proc.kill()


def ultimas(texto: str, n: int = 25) -> list[str]:
    return [l for l in texto.splitlines() if l.strip()][-n:]


# --------------------------------------------------------------------------- #
# Suite Python (unittest, un proceso por fichero)
# --------------------------------------------------------------------------- #
def ejecutar_fichero_python(fichero: Path) -> Resultado:
    modulo = f"tests.{fichero.stem}"
    res = Resultado(nombre=fichero.stem)
    t0 = time.perf_counter()
    codigo, salida, agotado = ejecutar(
        [sys.executable, "-m", "unittest", modulo, "-v"], RAIZ)
    res.duracion = time.perf_counter() - t0
    res.salida = salida

    if agotado:
        res.estado, res.motivo = FALLO, f"timeout de {TIMEOUT_S} s"
        res.lineas_fallo = ultimas(salida)
        return res

    m = re.search(r"^Ran (\d+) tests? in", salida, re.M)
    ejecutados = int(m.group(1)) if m else 0
    saltados = int(x.group(1)) if (x := re.search(r"skipped=(\d+)", salida)) else 0
    fallos = int(x.group(1)) if (x := re.search(r"failures=(\d+)", salida)) else 0
    errores = int(x.group(1)) if (x := re.search(r"errors=(\d+)", salida)) else 0

    # ¿Falla la importación por una dependencia externa que falta?
    faltan = {n.split(".")[0] for n in
              re.findall(r"No module named '([^']+)'", salida)}
    externas = sorted(faltan - MODULOS_PROPIOS)
    fallo_importacion = "Failed to import test module" in salida or "ModuleNotFoundError" in salida
    if codigo != 0 and externas and fallo_importacion and ejecutados <= 1:
        res.estado = OMITIDO
        res.motivo = "falta el módulo " + ", ".join(externas)
        return res

    # Fichero que se salta entero con unittest.SkipTest a nivel de módulo
    if codigo == 0 and ejecutados <= saltados and saltados > 0:
        mm = re.search(r"skipped '([^']*)'", salida) or re.search(r"skipped=\d+.*", salida)
        res.estado = OMITIDO
        res.motivo = mm.group(1) if mm and mm.lastindex else "todos los tests se omiten"
        res.ejecutados = 0
        return res

    if codigo == 0:
        res.estado = OK
        res.ejecutados = ejecutados
        res.pasados = ejecutados - saltados
        res.fallados = 0
        if saltados:
            res.motivo = f"{saltados} test(s) saltados"
    else:
        res.estado = FALLO
        res.ejecutados = ejecutados
        res.fallados = fallos + errores
        res.pasados = max(ejecutados - saltados - res.fallados, 0)
        res.lineas_fallo = lineas_fallo_unittest(salida)
    return res


def lineas_fallo_unittest(salida: str) -> list[str]:
    """Extrae de la salida de unittest los bloques FAIL/ERROR (hasta el resumen)."""
    lineas = salida.splitlines()
    inicio = next((i for i, l in enumerate(lineas)
                   if l.startswith(("FAIL:", "ERROR:"))), None)
    if inicio is None:
        return ultimas(salida)
    bloque = lineas[inicio:]
    return [l for l in bloque if l.strip()][:40]


def suite_python() -> list[Resultado]:
    ficheros = sorted(DIR_TESTS.glob("test_*.py"))
    if not ficheros:
        return [Resultado("python", OMITIDO, motivo="no hay tests/test_*.py")]
    resultados = []
    for f in ficheros:
        if sys.stdout.isatty():  # indicador de progreso solo en terminal
            print(f"  ... {f.name:<40}", end="\r", flush=True)
        resultados.append(ejecutar_fichero_python(f))
    if sys.stdout.isatty():
        print(" " * 50, end="\r")
    return resultados


# --------------------------------------------------------------------------- #
# Suite frontend (npm test -> vitest)
# --------------------------------------------------------------------------- #
def suite_frontend() -> Resultado:
    res = Resultado(nombre="frontend (vitest)")
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm") or shutil.which("npm")
    if not npm or not shutil.which("node"):
        res.estado = OMITIDO
        res.motivo = "no se encuentran node/npm en el PATH (instala Node.js)"
        return res
    if not (DIR_FRONTEND / "node_modules").is_dir():
        res.estado = OMITIDO
        res.motivo = "faltan dependencias: cd frontend && npm install"
        return res

    t0 = time.perf_counter()
    codigo, salida, agotado = ejecutar([npm, "test"], DIR_FRONTEND, {"CI": "1"})
    res.duracion = time.perf_counter() - t0
    res.salida = salida

    # Resumen de vitest: "Tests  1 failed | 11 passed (12)"
    m = re.search(r"^\s*Tests\s+(.*?)\((\d+)\)", salida, re.M)
    if m:
        res.ejecutados = int(m.group(2))
        pas = re.search(r"(\d+) passed", m.group(1))
        fal = re.search(r"(\d+) failed", m.group(1))
        res.pasados = int(pas.group(1)) if pas else 0
        res.fallados = int(fal.group(1)) if fal else 0

    if agotado:
        res.estado, res.motivo = FALLO, f"timeout de {TIMEOUT_S} s"
        res.lineas_fallo = ultimas(salida)
    elif codigo == 0:
        res.estado = OK
    else:
        res.estado = FALLO
        res.motivo = f"npm test terminó con código {codigo}"
        res.lineas_fallo = ultimas(salida)
    return res


# --------------------------------------------------------------------------- #
# Presentación
# --------------------------------------------------------------------------- #
def color(txt: str, estado: str) -> str:
    """Color ANSI solo si la salida es una terminal que lo soporta."""
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        return txt
    if os.name == "nt" and not (os.environ.get("WT_SESSION") or os.environ.get("ANSICON")):
        return txt
    cod = {OK: "32", FALLO: "31", OMITIDO: "33"}[estado]
    return f"\x1b[{cod}m{txt}\x1b[0m"


def num(v: int | None) -> str:
    return "-" if v is None else str(v)


def imprimir_tabla(resultados: list[Resultado]) -> None:
    cab = f"{'Suite':<28}{'Estado':<10}{'Ejec.':>6}{'Pasan':>7}{'Fallan':>8}{'Tiempo':>9}"
    print(cab)
    print("-" * len(cab))
    for r in resultados:
        estado = color(f"{r.estado:<10}", r.estado)
        print(f"{r.nombre[:27]:<28}{estado}{num(r.ejecutados):>6}{num(r.pasados):>7}"
              f"{num(r.fallados):>8}{r.duracion:>8.1f}s")
    print("-" * len(cab))


def main() -> int:
    ap = argparse.ArgumentParser(description="Ejecuta todos los tests de NEXO.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--solo-python", action="store_true", help="solo tests de Python")
    g.add_argument("--solo-frontend", action="store_true", help="solo tests del frontend")
    ap.add_argument("-v", "--detallado", action="store_true",
                    help="muestra la salida completa de cada suite")
    ap.add_argument("--estricto", action="store_true",
                    help="trata las suites OMITIDAS como fallo")
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):  # evita errores de codificación en Windows
        sys.stdout.reconfigure(errors="replace")

    resultados: list[Resultado] = []
    if not args.solo_frontend:
        print("== Tests de Python ==")
        resultados += suite_python()
    if not args.solo_python:
        print("== Tests del frontend ==")
        resultados.append(suite_frontend())

    print()
    for r in resultados:
        if args.detallado and r.salida:
            print(f"##### {r.nombre} #####\n{r.salida.rstrip()}\n")
        if r.estado == FALLO and not args.detallado:
            print(f"--- FALLO en {r.nombre}" + (f" ({r.motivo})" if r.motivo else ""))
            for l in r.lineas_fallo:
                print("    " + l)
            print()
    imprimir_tabla(resultados)

    omitidas = [r for r in resultados if r.estado == OMITIDO]
    for r in omitidas:
        print(f"  OMITIDO {r.nombre}: {r.motivo}")
    tot = [r for r in resultados if r.ejecutados is not None]
    print(f"Total: {sum(r.ejecutados for r in tot)} tests ejecutados, "
          f"{sum(r.pasados or 0 for r in tot)} pasan, "
          f"{sum(r.fallados or 0 for r in tot)} fallan; "
          f"{len(omitidas)} suite(s) omitida(s).")

    hay_fallos = any(r.estado == FALLO for r in resultados)
    if hay_fallos:
        print("HAY FALLOS")
    elif omitidas:
        print("CORRECTO, PERO CON SUITES OMITIDAS" +
              (" (modo --estricto: se considera fallo)" if args.estricto else ""))
    else:
        print("TODO CORRECTO")
    return 1 if hay_fallos or (args.estricto and omitidas) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario (Ctrl+C).")
        sys.exit(130)
