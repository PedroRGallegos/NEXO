# Auditoría del proyecto NEXO (subagente A, solo lectura)

> **Nota (27/11/2026):** documento histórico de una revisión anterior. Desde entonces la paleta pasó de ámbar a azul y violeta, la sorpresa del «67» se eliminó (solo queda «Fernando Alonso») y hay más tests. El estado actual está en `README.md`, `CAMBIOS.md` (revisiones 14 a 17) y `docs/PRUEBAS.md`.

Proyecto auditado: `/home/claude/work/nexo_interfaz/07_NEXO_Interfaz/nexo`.
Enunciado: `Proyecto_POO_por_capas_-_NEXO__tu_primer_agente_de_IA.pdf` (texto extraído con `pdftotext`).

Qué se comprobó y cómo:
- Lectura del enunciado completo y de `dominio/mensaje.py`, `dominio/herramientas.py`, `presentacion/chat_consola.py`, `persistencia/*`, `servicios/agente.py`, `presentacion/api.py` y `README.md`.
- Análisis estático con scripts propios: clases CSS frente a uso en TSX, imports y funciones Python con `ast`, exports TS por `grep`.
- No se ejecutó ningún test ni la aplicación (faltan `httpx`, `tenacity` y `fastapi` en el entorno). La cobertura se ha deducido de leer el código, no de ejecutarlo.

---

## 1. Requisitos del enunciado y cobertura

### Núcleo (Nivel 1, sección 12)
| # | Requisito | Cubre | Evidencia |
|---|---|---|---|
| 1 | Estructura con 4 capas y `main.py` | Sí | carpetas `dominio/ servicios/ persistencia/ presentacion/`, `main.py` |
| 2 | 3 herramientas que heredan de `Herramienta` con `super()` | Sí | `Calculadora`, `ConversorMoneda`, `BuscadorFAQ` en `dominio/herramientas.py` |
| 3 | 2 modelos hijos de `Modelo`, intercambiables con `/modelo` | Sí | `ModeloEco`, `ModeloReglas` en `dominio/modelos.py`; `_cmd_modelo` en `chat_consola.py` |
| 4 | Lista de mensajes privada (`__mensajes`) con acceso por métodos y `get_mensajes()` devuelve copia | Sí | `mensaje.py` líneas 93 y 137 |
| 5 | Agente por polimorfismo, sin `isinstance` por tipo | Sí | `agente.py::_ejecutar_herramienta` usa `self._herramientas.get(nombre)` |
| 6 | ≥3 excepciones propias lanzadas en dominio/servicio y capturadas en presentación | Sí | `dominio/excepciones.py` (8 clases); captura en `chat_consola.py` (no verificada línea a línea) |
| 7 | Sin `print()` ni `input()` en `dominio/` ni `servicios/` | Sí | `grep` solo encuentra la palabra en un docstring de `agente.py:9` |
| 8 | El ejemplo de ejecución de la sección 8 funciona | No comprobado | no se ejecutó; la lógica de `ModeloReglas` lo contempla |
| 9 | `Mensaje`: roles válidos, `ValueError`, `__str__`, `to_dict` | Sí | `mensaje.py` 18-80 |
| 10 | `Conversacion`: `id`, límite 500 por defecto, `LimiteContextoSuperado`, `tokens_estimados` (palabras × 1,3) | Sí | `mensaje.py` 83-146 |
| 11 | `Respuesta` con `es_llamada_herramienta()` | Sí | `modelos.py` 55-69 |
| 12 | Bucle del agente con máximo 3 vueltas, `HerramientaNoEncontrada`, `ArgumentosInvalidos` convertido en mensaje | Sí | `agente.py` 19, 65-91, 128-160 |

### Nivel 2
| # | Requisito | Cubre | Evidencia |
|---|---|---|---|
| 13 | `RepositorioConversaciones` con guardar/cargar/listar y `from_dict` | Sí | `persistencia/repositorio_conversaciones.py`; `from_dict` en `mensaje.py` |
| 14 | `RegistroUso` CSV con `resumen()` | Parcial | existe, pero la cabecera difiere del enunciado (ver sección 2.5) |
| 15 | Comandos `/herramientas /modelo /salir /historial /guardar /cargar /lista /nueva /stats` | Sí | `chat_consola.py` 61-71 (más `/esquemas` y `/ayuda`, no pedidos) |

### Nivel 3 (retos, cada uno hasta +0,5)
| # | Reto | Cubre | Evidencia |
|---|---|---|---|
| 16 | Herramienta nueva sin tocar el agente | Sí | `ConsultaStock`, `Reloj`; se añaden en `main.py::construir_herramientas` |
| 17 | `ModeloLLM` real | Sí en código, nunca probado contra proveedor | `modelos.py` 269-454; tests con `httpx.MockTransport` |
| 18 | `esquema()` JSON Schema | Sí | `herramientas.py:72` |
| 19 | Varias herramientas en una pregunta | Sí | `ModeloReglas._encadenar_calculo` |
| 20 | Tests pytest del dominio | Sí | 93 funciones `test_*` en 6 ficheros (17+26+17+11+14+8) |
| 21 | Resumen automático al 80 % | Sí | `agente.py` `_compactar_si_hace_falta` y `Conversacion.compactar` |

### Entrega (sección 14)
| # | Requisito | Cubre | Evidencia |
|---|---|---|---|
| 22 | README con ejecución, nivel y retos | Sí | `README.md` secciones 2-3 |
| 23 | Diagrama de clases | Sí | Mermaid en `README.md` sección 6 |
| 24 | Uso de la IA | Sí | `README.md` sección 8 |
| 25 | Respuestas de reflexión | Sí | `README.md` sección 9 |
| 26 | Zip sin `.venv/` | Pendiente | el zip original de usuario incluía `node_modules` (~78 MB) y `datos/` |

### Fuera del enunciado (no exigido)
- API web FastAPI, `GestorConversaciones`, panel de estadísticas, panel de configuración, logo, esfera de canvas y los extras 67 / Alonso.
- El enunciado solo menciona React como futuro (Tema 8), así que la web es una ampliación.
- No son un fallo, pero cuentan como alcance extra.

---

## 2. Código y recursos prescindibles (con evidencia)

### 2.1 CSS sin uso
174 clases CSS distintas; tras descartar clases dinámicas (comprobadas a mano: `app--con-panel`, `boton--activo`, `herramienta--error`, `medidor__relleno--alto`, `nexo-visual--hablando/pensando`, `opcion--activa`, `sidebar--abierta`, `logo--animado`, `huevo__confeti--N`) quedan **sin ninguna referencia en TSX**:
- `marca__logo`, `bienvenida__glifo` (sustituidos por `<Logo/>`).
- Capas del núcleo antiguo en `componentes.css`: `nexo-visual__anillo` (+ `--exterior`, `--fragmentado`, `--medio`, `--interior`), `__anillo-nucleo`, `__arco`, `__aura-orbe`, `__barrido`, `__eje`, `__enlace`, `__esfera`, `__esfera-aura`, `__esfera-cascaron`, `__halo`, `__luz-nucleo`, `__malla`, `__meridiano`, `__nodo` (+ `--brillante`), `__orbita` (+ `--a/b/c`), `__orbitas`, `__paralelo`, `__particulas`, `__punto-nucleo`, `__superficie`.
- `nexo-visual__onda` (las barras radiales) ya no aparece en `NexoFace.tsx`: la coincidencia de `grep` es `__onda-lateral`, que sí se usa. La clase base `__onda` queda sin uso; no lo verifiqué contra `esfera.css`.
- Tamaño: `componentes.css` 31,7 KB de un total de 50 KB de CSS; buena parte es el núcleo antiguo. No medí cuánto exactamente: habría que borrar y recompilar.

### 2.2 TypeScript
- `NexoFace.tsx` (142 líneas) más `EsferaJarvis.tsx` (440 líneas): la lógica de la esfera está duplicada en CSS antiguo y canvas nuevo.
- Todos los `export` tienen al menos un uso (comprobado por `grep -w`). No hay código muerto claro en TS.
- `api.herramientas()` y `api.modelos()` se usan solo en `PanelConfig`; `api.crear()`, `api.listar()`, `api.salud()` en `useChat`.

### 2.3 Python
- `ast`: sin imports sin uso. `enviar_stream` aparece como «sin referencias» pero es un manejador de ruta decorado, así que es falso positivo.
- Endpoint `POST /api/conversaciones/{id}/mensajes` (no streaming): el frontend usa solo `/mensajes/stream`. Solo lo usan los tests, así que **es API duplicada**.
- `RegistroUso.registrar_llm` / `resumen_llm` y `ModeloLLM`: no se usan sin `LLM_API_KEY`; son reto 2 del enunciado, se conservan.

### 2.4 Dependencias
- Python (`requirements.txt`): `fastapi`, `uvicorn`, `python-dotenv`, `httpx`, `tenacity`, todas con uso. `pydantic` llega con FastAPI.
- `requirements.txt` dice «Solo para la interfaz web. La consola funciona solo con la biblioteca estándar», pero `dominio/modelos.py` importa `httpx`, `dotenv` y `tenacity` al cargar el módulo. **Falso: `python main.py` también necesita esas dependencias.** (Mejorar: importación perezosa o corregir el comentario.)
- Node: solo `react` y `react-dom` en runtime (bien). Dev: `vite`, `vitest`, `typescript`, `@vitejs/plugin-react`, `@types/*`, todos con uso.
- `node_modules/` del zip original: 78 MB, solo binarios de Windows; no debería entregarse.

### 2.5 Registro de uso (`uso.csv`)
- Cabecera real: `timestamp,question,output_tokens,cost,fecha,herramienta,argumentos,exito,milisegundos`.
- El enunciado pide `fecha,herramienta,argumentos,exito,milisegundos`. Las filas de herramientas dejan 4 columnas vacías y las del LLM dejan 5. Es un esquema mixto: **Mejorar** (dos ficheros o columnas del enunciado primero).

### 2.6 Datos simulados o decorativos presentados como lecturas
En `NexoFace.tsx` y `EsferaJarvis.tsx`:
- «CARGA DEL SISTEMA» (`NexoFace.tsx:26-27`) es un número aleatorio entre 12 y 48 que cambia cada 1,8 s. **No es una lectura real.**
- «218 Hz · ACTIVA» (`:116`) es un valor fijo.
- «MALLA 1700 PTS · ANILLOS 05» y «RADIO 1.000 · ESCALA 1.06/0.95/1.00» son constantes de dibujo mostradas como telemetría.
- «ENLACE LOCAL · ACTIVO», «SEÑAL ESTABLE», «NÚCLEO EN LÍNEA», «MATRIZ NEURAL ACTIVA», «SISTEMA OPERATIVO» y «VISUAL CORE SINCRONIZADO» son texto fijo. La barra lateral sí usa el estado real (`conectado`), así que pueden contradecirse con el servidor caído.
- Líneas de arranque de la bienvenida (`Chat.tsx`): texto fijo, no un estado real.
- `/api/estadisticas`: los tokens se estiman como palabras × 1,3 sobre el historial (rotulado con asterisco y nota). El coste va rotulado «€» con una tarifa configurable; es estimación.

### 2.7 Rendimiento (evidencia estática)
- `EsferaJarvis.tsx`: 1700 partículas y 70 rayos animados con `requestAnimationFrame` continuo; el subagente que la hizo midió 30-33 fps sin GPU. Va contra el criterio «evitar animaciones continuas».
- `NexoFace.tsx`: `setInterval` de 1,8 s que re-renderiza solo para el número aleatorio.
- `cyberpunk.css`: `body::before` a pantalla completa con `mix-blend-mode: multiply` y `body::after` con viñeta; coste de composición no medido.
- `dist`: `index.js` 258 KB y `index.css` 40,6 KB (sin comprimir).
- `GestorConversaciones`: agentes y cerrojos en memoria sin límite; `_estadisticas` relee todo el disco en cada petición.
- No se midió tiempo de carga ni memoria.

---

## 3. Clasificación

| Elemento | Decisión | Justificación |
|---|---|---|
| Dominio (`mensaje`, `herramientas`, `modelos`, `excepciones`) | Conservar | Cumple el enunciado y los retos 1, 3, 4, 6 |
| `servicios/agente.py` | Conservar | Bucle correcto, máximo 3 vueltas, resumen automático |
| `presentacion/chat_consola.py` | Conservar | Todos los comandos del Nivel 2 |
| `persistencia/repositorio_conversaciones.py` | Conservar | Escritura atómica y validación de id |
| `persistencia/registro_uso.py` | Mejorar | Cabecera mezclada y distinta de la del enunciado |
| `ModeloLLM` + `registrar_llm` | Conservar | Reto 2 opcional; sin probar contra proveedor real |
| `requirements.txt` (comentario) | Mejorar | Dice que la consola no necesita dependencias, pero `modelos.py` importa `httpx`/`tenacity`/`dotenv` |
| API FastAPI (`api.py`, `esquemas_api.py`, `gestor_conversaciones.py`) | Conservar | Necesaria para la interfaz web |
| `POST /mensajes` no streaming | Eliminar o dejar solo para tests | El frontend no lo usa; duplica el flujo del streaming |
| Hook `useChat.ts`, `cliente.ts`, `sse.ts` | Conservar | Pequeños, con tests de SSE |
| Esfera de canvas (`EsferaJarvis.tsx`, 440 líneas) | Rehacer | Animación continua pesada; reducir partículas y fotogramas, y pausar en reposo |
| `NexoFace.tsx` HUD | Rehacer | Mezcla telemetría real con valores aleatorios o fijos |
| CSS del núcleo antiguo en `componentes.css` | Eliminar | ~30 clases sin referencia (sección 2.1) |
| `marca__logo`, `bienvenida__glifo` | Eliminar | Sustituidos por `<Logo/>` |
| `cyberpunk.css` (capa de sobrescritura) | Mejorar | Fusionar con `componentes.css` en vez de dos hojas que se pisan |
| Panel Configuración / Estadísticas | Conservar (mejorar) | Útiles para elegir modelo y ver uso; el coste en «€» es solo estimación |
| Logo (`Logo.tsx`, `logo.css`) | Conservar | Ligero, sin filtros |
| Easter eggs (`huevos.ts`, `Huevo.tsx`) | Conservar | Lógica aislada y con tests |
| `node_modules/` y `datos/` en el zip | Eliminar | No deben entregarse (el enunciado pide zip sin `.venv`) |
| `CAMBIOS.md`, `docs/INFORME.md`, `GUIA_FUNCIONAMIENTO.md` | No comprobado | No leídos; pueden estar desactualizados tras los cambios visuales |

## 4. Límites de esta auditoría
- No se ejecutaron tests ni la aplicación.
- La lectura fue parcial en `chat_consola.py` (captura de `ErrorAgente`), `INFORME.md` y `GUIA_FUNCIONAMIENTO.md`.
- La detección de CSS sin uso es textual: no cubre clases generadas por concatenación más compleja (se revisaron a mano las dinámicas conocidas).
