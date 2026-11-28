# Pruebas de NEXO

Un solo comando ejecuta todos los tests del proyecto (Python y frontend) y
muestra un resumen:

```bash
python ejecutar_tests.py
```

Funciona desde cualquier carpeta (las rutas se calculan a partir del propio
script) y solo usa la biblioteca estándar de Python.

## Opciones

| Opción | Efecto |
|---|---|
| `--solo-python` | Solo los tests de `tests/`. |
| `--solo-frontend` | Solo `npm test` (vitest) en `frontend/`. |
| `-v`, `--detallado` | Muestra la salida completa de cada suite. Por defecto solo el resumen y, si algo falla, las líneas del fallo. |
| `--estricto` | Trata las suites OMITIDAS como fallo (útil en integración continua). |

Código de salida: `0` si no hay fallos, `1` si hay alguno (o si hay omitidas
con `--estricto`), `130` si se interrumpe con Ctrl+C. Cada suite tiene un
tiempo máximo de 300 s.

## Qué cubre cada suite

Python (un fichero = una fila de la tabla; cada uno se ejecuta en su propio proceso):

| Fichero | Cubre | Necesita |
|---|---|---|
| `test_dominio.py` | Capa de dominio (sin `input()`/`print()`). | `httpx`, `tenacity`, `python-dotenv` |
| `test_agente_y_persistencia.py` | Agente, persistencia y chat (datos en carpetas temporales). | ídem |
| `test_mejoras.py` | Nuevas herramientas, esquemas JSON, encadenado, resumen automático, robustez. | ídem |
| `test_robustez.py` | Regresiones al intentar romper el programa (sin FastAPI). | ídem |
| `test_sorpresas.py` | Sorpresas del chat (misma detección que `huevos.test.ts` del frontend). | ídem |
| `test_streaming_y_gestor.py` | `Agente.procesar_por_pasos` y `GestorConversaciones` (sin FastAPI). | ídem |
| `test_llm_compatibilidad.py` | Compatibilidad de `ModeloLLM` con Groq y otros proveedores (tokens, errores, tope ampliado, razonamiento) con cliente simulado. | `httpx`, `tenacity`, `python-dotenv` |
| `test_modelo_llm.py` | Modelo remoto sin llamadas de red ni claves reales. | además `fastapi` |
| `test_api.py` | API web (FastAPI) con `TestClient`, sin red ni modelos de pago. | `fastapi`, `httpx` |

Recuento estático de funciones `test_*`: 120 en total; sin `test_api.py` (19) ni `test_modelo_llm.py` (11), que necesitan FastAPI, son 90.

Frontend: `npm test` ejecuta `vitest run` sobre los tests de TypeScript (`api/sse`, `formato`, `huevos`, `imagenes`, `modelos`, `voz` y `comandos`; unos 35 casos). No se han podido ejecutar en el entorno de desarrollo.

Para probar el proveedor LLM real (no es un test automático): `python probar_llm.py`.

## Cómo se ejecutan los tests de Python

Se usa `python -m unittest tests.<fichero>` con el mismo intérprete que lanza
el script (`sys.executable`). Se eligió `unittest` y no `pytest` porque los
tests están escritos con `unittest`, es de la biblioteca estándar (no añade
dependencias) y su salida es estable de interpretar. Los tests siguen siendo
compatibles con `pytest` (`pytest.ini` los descubre) si prefieres lanzarlos a mano.

## Estados

- **OK**: la suite terminó y todo pasó (los tests saltados se indican aparte).
- **FALLO**: algún test falla, hay un error en el código, la suite no termina
  a tiempo o `npm test` devuelve error. Se muestran las líneas del fallo.
- **OMITIDO**: no se pudo ejecutar por falta de algo en el entorno (no es un
  fallo del código). Se indica el motivo, p. ej. `falta el módulo fastapi`.

Mensaje final: `TODO CORRECTO`, `HAY FALLOS` o
`CORRECTO, PERO CON SUITES OMITIDAS`.

## Si faltan dependencias

- Python: `pip install -r requirements-dev.txt` (incluye lo necesario para la
  API y los tests). Use el mismo intérprete con el que ejecuta el script.
  Si aparece `falta el módulo X`, instale ese paquete.
- Frontend: necesita Node.js y npm en el PATH y `cd frontend && npm install`.
  Sin `frontend/node_modules` o sin `npm`, la suite sale OMITIDA con la orden
  a ejecutar. En Windows se usa `npm.cmd` automáticamente.
- Si `npm test` falla con un error de binarios (p. ej. de `rollup`) o
  `Permission denied`, reinstale: borre `frontend/node_modules` y ejecute
  `npm install` de nuevo en la propia máquina (no copie `node_modules` entre
  sistemas operativos).
