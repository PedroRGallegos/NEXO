"""Prueba ModeloLLM sin servidor: lee .env, llama al proveedor y muestra la respuesta real.

Uso (desde la carpeta nexo):  python3 probar_llm.py
        python3 probar_llm.py --modelos   (lista los modelos que tu clave puede usar)
Solo biblioteca estándar. No imprime la clave (solo su prefijo y longitud).
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def leer_env(ruta: Path) -> dict:
    datos = {}
    if not ruta.is_file():
        return datos
    for linea in ruta.read_text(encoding="utf-8-sig").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        datos[clave.strip()] = valor.strip().strip('"').strip("'")
    return datos


def listar_modelos(url: str, clave: str) -> None:
    base = url.split("/chat/completions")[0]
    peticion = urllib.request.Request(
        f"{base}/models",
        headers={"Authorization": f"Bearer {clave}", "User-Agent": "nexo-probar-llm/1.0"},
    )
    try:
        with urllib.request.urlopen(peticion, timeout=30) as r:
            datos = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}")
        print(e.read().decode(errors="replace")[:600])
        return
    except urllib.error.URLError as e:
        print("No se pudo conectar:", e.reason)
        return
    ids = sorted(m["id"] for m in datos.get("data", []))
    print("\nModelos disponibles para tu clave (copia uno en LLM_MODEL):")
    for i in ids:
        print("  ", i)


def main() -> None:
    ruta = Path(__file__).resolve().parent / ".env"
    env = leer_env(ruta)
    print(f"Archivo .env: {ruta} -> {'existe' if ruta.is_file() else 'NO EXISTE'}")
    clave = env.get("LLM_API_KEY") or os.getenv("LLM_API_KEY", "")
    url = env.get("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
    modelo = env.get("LLM_MODEL", "gpt-4o")
    print(f"Clave: {clave[:4]}… (longitud {len(clave)}){'  <-- VACÍA' if not clave else ''}")
    if clave != clave.strip() or " " in clave:
        print("AVISO: la clave tiene espacios.")
    print(f"URL:    {url}")
    print(f"Modelo: {modelo}")
    if "groq" in url and not clave.startswith("gsk_"):
        print("AVISO: la URL es de Groq pero la clave no empieza por gsk_.")
    if "openai.com" in url and clave.startswith("gsk_"):
        print("AVISO: la clave es de Groq pero la URL es de OpenAI. Cambia LLM_API_URL y LLM_MODEL.")

    if "--modelos" in sys.argv:
        listar_modelos(url, clave)
        return

    cuerpo = json.dumps(
        {
            "model": modelo,
            "messages": [{"role": "user", "content": "Responde solo: hola"}],
            "max_tokens": 20,
        }
    ).encode()
    peticion = urllib.request.Request(
        url,
        data=cuerpo,
        method="POST",
        headers={
            "Authorization": f"Bearer {clave}",
            "Content-Type": "application/json",
            "User-Agent": "nexo-probar-llm/1.0",
        },
    )
    print("\nLlamando al proveedor…")
    try:
        with urllib.request.urlopen(peticion, timeout=30) as r:
            datos = json.loads(r.read().decode())
        print("HTTP 200 · respuesta:", datos["choices"][0]["message"]["content"])
        print("\nLa conexión, la clave y el modelo funcionan.")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}")
        print(e.read().decode(errors="replace")[:600])
    except urllib.error.URLError as e:
        print("No se pudo conectar:", e.reason)


if __name__ == "__main__":
    main()
