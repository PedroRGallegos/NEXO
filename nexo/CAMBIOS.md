# Cambios de esta revisión

## Errores corregidos
- **Frontend (`useChat.ts`)**: si cambiabas de conversación mientras NEXO respondía, la respuesta se pintaba en la conversación equivocada. Ahora solo se aplica si sigue siendo la visible.
- **Frontend (`sse.ts`)**: el lector SSE no entendía saltos de línea `\r\n` (válidos según la especificación). Añadido con test.
- **Frontend (`Mensaje.tsx`)**: temporizador del botón «copiar» sin limpiar al desmontar.
- **API (`api.py`)**: `PeticionInvalida` (parámetros del LLM fuera de rango) devolvía un 500 genérico; ahora 422 `peticion_invalida`.

## Extras
- Escribir `67` (o «six seven») mostraba un robot original haciendo el gesto (eliminado en la revisión 15).
- Escribir `Fernando Alonso` muestra un piloto genérico celebrando una victoria.
- Respetan `prefers-reduced-motion`, se cierran solos o con clic y no se activan dentro de frases normales.

## Higiene del repositorio
- Se retiran `frontend/node_modules` (~80 MB, solo binarios de Windows) y `datos/` (datos generados, ya en `.gitignore`).
- `frontend/dist` se regeneró con esbuild; para el build oficial usa `npm install && npm run build`.

## Pendiente / recomendado
- `GestorConversaciones` guarda agentes y cerrojos en memoria sin límite: conviene una caché con tope.
- `_estadisticas` relee todas las conversaciones de disco en cada petición.
- El coste se calcula con una tarifa configurable (`LLM_COST_PER_1K_OUTPUT`) y se muestra como euros: es una estimación, no la factura del proveedor.
- Nunca se ha probado contra un proveedor LLM real.

## Mejoras visuales (revisión 2)
- Nuevo logo (`Logo.tsx`, `logo.css`): emblema de anillos fragmentados con núcleo hexagonal, marcas de calibración y esquinas de enfoque. También es el favicon.
- Nueva esfera de IA (`EsferaJarvis.tsx`, `esfera.css`): canvas con ~1700 partículas y trazos ámbar, anillos fragmentados, núcleo que late y estados de espera, pensando y hablando. Se pausa si la pestaña no es visible y no anima con `prefers-reduced-motion`.
- `NexoFace.tsx`: HUD con escalas y lecturas; se retiran las capas decorativas antiguas.
- Quedan reglas CSS sin uso en `componentes.css` (`.nexo-visual__anillo`, `__esfera`, `__onda`, `.marca__logo`, `.bienvenida__glifo`): pueden borrarse.
- Rendimiento medido en Chromium sin GPU: 30–33 fps. En un equipo con GPU debería ir mejor, pero no se ha medido.

## Identidad cyberpunk (revisión 3)
- Nueva hoja `frontend/src/estilos/cyberpunk.css`, cargada la última: paleta ámbar, cian y magenta; rejilla, líneas de barrido y viñeta de fondo; esquinas biseladas; franjas de peligro; tipografía HUD en mayúsculas.
- Mensajes como registro de terminal («OPERADOR //» y «NEXO //»), herramientas como líneas «EXEC» con franja de peligro, historial numerado, línea de comandos y paneles con cabeceras propias.
- Bienvenida con líneas de arranque y efecto glitch ocasional en el título.
- El HUD de la esfera se compacta cuando el panel lateral está abierto (consulta de contenedor).
- Las variables `--magenta` y `--violeta` eran azules; ahora son magenta y violeta reales.
- No se cargan tipografías externas: se usan las del sistema, por lo que el aspecto de la fuente varía según el equipo.

## Rediseño y limpieza (revisión 4)
- HUD de la esfera con datos reales; sin cifras inventadas ni intervalos de re-render.
- Esfera con tope de 20 fps en reposo y 30 con actividad; se retiran las capas de pantalla completa.
- 81 selectores CSS sin uso eliminados (script de poda comprobado contra el código).
- Easter eggs en un registro (`huevos.ts`); «Fernando Alonso» se detecta como frase completa y se muestra bien escrito.
- Informe completo en `docs/INFORME_REDISENO.md` y auditoría en `docs/AUDITORIA.md`.

## Cumplimiento del enunciado en la interfaz (revisión 5)
- Las herramientas muestran sus argumentos, como en el ejemplo del enunciado.
- Aviso «Modelo cambiado a …» al cambiar de modelo.
- Cabecera con «sesión <id> · guardada» (guardado automático).
- Lista completa en `docs/CUMPLIMIENTO_ENTORNO_GRAFICO.md`.

## Documentación (revisión 6)
- README: sección 8 (uso de la IA) completada con lo realizado, salvo los puntos que solo pueden rellenar las personas autoras; sección 10 actualizada; capturas nuevas en `docs/`.
- `GUIA_FUNCIONAMIENTO.md`: equivalencias consola-interfaz y descripción de la esfera y las sorpresas.

## Ejecución real y corrección en móvil (revisión 7)
- Se arrancó la API y se probó la interfaz con un navegador real. En pantallas de 760 px o menos la barra lateral ocupaba 36 px del alto y el botón «Enviar» quedaba fuera de la ventana: `cyberpunk.css` (cargado después) sobrescribía `position: fixed` con `relative`. Corregido en `cyberpunk.css`.
- `frontend/dist` regenerado con esbuild a partir del código actual.
- Un tester adversarial (subagente) atacó la API y la interfaz. Corregido y con tests en `tests/test_robustez.py`:
  - Si el cliente cortaba el streaming, la conversación seguía bloqueada ~40 s. Ahora el trabajo corre en un hilo propio que suelta el cerrojo al terminar.
  - Un número de 400 cifras producía `inf` y un 500 (o un JSON no válido en el stream). Ahora se envía como texto.
  - Un id de conversación muy largo daba 500; ahora 404.
  - Un fichero de conversación con JSON anidado en exceso o con `fecha` de tipo raro, o una fila rara de `uso.csv`, ya no tumban el listado ni las estadísticas.
- Conocido y sin cambiar: la calculadora entiende mal `-5 + 3`, fechas como `2024-05-01` o `1e5`; el modelo de reglas puede elegir mal producto en stock; con el modelo `eco` un mensaje de ~200 palabras supera el límite de 500 tokens; el límite de contexto no compacta antes de rechazar; faltan cabeceras de seguridad HTTP y paginación del historial.

## Preparación para GitHub (revisión 8)
- `.gitignore`: `frontend/dist/` ya se sube (antes estaba excluido y quien clonaba no tenía interfaz sin instalar Node); `.env` y `.env.*` quedan excluidos salvo `.env.example`; se excluyen también `*Zone.Identifier`, `.rar` y `.zip`.
- Nuevo `.gitignore` en la carpeta superior por si el repositorio se inicia allí.

## Comando /limpiar (revisión 9)
- Consola y web: `/limpiar` deja la conversación en blanco sin perder lo anterior, que queda en el historial. En la web también vale `/clear` y no se envía al agente. Si la conversación ya está vacía, avisa y no crea otra; en la consola, sin memoria en disco, no limpia para no perder el historial.
- Tests nuevos: 3 en la consola (`tests/test_agente_y_persistencia.py`) y `frontend/src/comandos.test.ts`.

## La esfera «habla» (revisión 10)
- Nuevo `frontend/src/voz.ts`: convierte el texto de la respuesta en un nivel de voz (una subida por sílaba, pausas en comas y puntos; acelera si hay mucho texto para no ir por detrás). Con tests en `voz.test.ts`.
- `EsferaJarvis`: el núcleo late con cada sílaba, salen ondas de sonido, aparece un anillo ecualizador azul y la esfera se expande y brilla con el nivel de voz. El estado «Respondiendo» dura lo que tarda en decirse el texto.
- Sin audio. Con movimiento reducido del sistema la esfera sigue estática.

## Respuestas de las sorpresas (revisión 11)
- Antes, al activar una sorpresa se veía la animación pero el chat contestaba «No estoy seguro, ¿puedes reformularlo?». Ahora `ModeloReglas` responde: «SIX SEVEEEEEEEEEEEEEEEN» a `67` y la foto aportada por el equipo a «Fernando Alonso». Las animaciones no se han tocado.
- Nuevo `dominio/sorpresas.py` (mismos criterios de detección que `huevos.ts`) y `frontend/src/imagenes.ts`, que convierte la marca `[[imagen:/sorpresas/...]]` en una imagen y rechaza cualquier otra ruta. La foto está en `frontend/public/sorpresas/`.
- Con el modelo `eco` sigue valiendo el eco («Has dicho: 67»): solo `reglas` conoce las sorpresas.
- La foto es una imagen real aportada por el equipo: falta anotar su fuente y licencia (ver `Referencias.md`).

## Ejecutor de todos los tests (revisión 12)
- Nuevo `ejecutar_tests.py` (solo biblioteca estándar): lanza los tests de Python (cada fichero por separado) y los del frontend, y muestra una tabla con estado, nº de tests y tiempo. Distingue OK, FALLO y OMITIDO (falta una dependencia, con el motivo). Devuelve código 1 si algo falla; `--estricto` cuenta también lo omitido. Documentado en `docs/PRUEBAS.md`.
- Hecho por un subagente y verificado aquí: 79 tests de Python pasan. El frontend no se pudo ejecutar en este entorno (vitest sin permiso de ejecución), por lo que el recuento de vitest y el comportamiento en Windows no están probados.

## ModeloLLM separado en Configuración (revisión 13)
- `GET /api/modelos` devuelve siempre reglas, eco y llm, con `tipo` (local/remoto), `disponible`, `motivo` y `detalle` (contrato en `docs/API.md`). Cambiar a un modelo no disponible da 422 `modelo_no_disponible` con el motivo. Cambios en `servicios/gestor_conversaciones.py`, `presentacion/api.py`, `main_web.py` y un atributo `remoto` en `Modelo`.
- Panel Configuración: grupo «Modelos locales» y, separado, «Modelo remoto · API». Sin clave, ModeloLLM sale desactivado con «NO CONFIGURADO» y el motivo. Con `src/modelos.ts` y sus tests.
- Corregido otro fallo de mi restyle: en pantallas de 1100 px o menos los paneles de Configuración y Estadísticas quedaban aplastados (`cyberpunk.css` anulaba `position: fixed`).
- Hecho con dos subagentes en paralelo (backend y frontend). Verificado aquí con la API real y el navegador; `tests/test_api.py` (2 casos nuevos) no se ha podido ejecutar sin FastAPI.

## ModeloLLM tolerante a Groq y otros proveedores (revisión 14)
- Sigue usando la API de chat completions de OpenAI; Groq la ofrece en `https://api.groq.com/openai/v1/chat/completions` (el modelo de ejemplo de entonces, `llama-3.3-70b-versatile`, se sustituyó más abajo por `openai/gpt-oss-120b`). `.env.example` trae las dos opciones.
- Los tokens de salida se leen de `usage` o de `x_groq.usage`; si el proveedor no los envía en streaming se estiman (~4 caracteres por token) en vez de fallar.
- Si el modelo pide varias herramientas a la vez se atiende la primera (antes era un error).
- Los errores HTTP incluyen el motivo que da el proveedor (clave inválida, modelo inexistente, límite...), p. ej. «El proveedor rechazó la petición (HTTP 401). Motivo: ...».
- Tests nuevos en `tests/test_llm_compatibilidad.py` (4, con cliente simulado). No se ha podido probar contra Groq real: este entorno no tiene salida a internet.
- (rev. 14) La API ya no oculta el error del proveedor LLM tras «No se pudo completar la petición al modelo.»: muestra el texto de `ModeloLLM` (código HTTP y motivo del proveedor, nunca la clave) para poder diagnosticar claves, modelos o límites.
- (rev. 14) Modelo por defecto para Groq: `openai/gpt-oss-120b` (Groq retiró `llama-3.3-70b-versatile` el 16/08/2026, error HTTP 404). Los modelos gpt-oss razonan y gastan tokens pensando; por eso se amplió el tope (primero `LLM_MAX_TOKENS=1000`, luego el esquema 500/1000 descrito a continuación). `python3 probar_llm.py --modelos` lista los modelos de tu clave.
- (rev. 14) Límite de respuesta del LLM: tope normal 500 tokens (`LLM_MAX_TOKENS`); si la respuesta se corta (`finish_reason: length`) se continúa automáticamente hasta 1000 en total (`LLM_MAX_TOKENS_AMPLIADO=1000`, 0 desactiva). Además se envía una instrucción de concisión (`LLM_SYSTEM`) y, si se define, `LLM_REASONING_EFFORT` (p. ej. `low` en gpt-oss) para que el razonamiento no se coma los tokens. Con tests en `tests/test_llm_compatibilidad.py`. Sin probar contra Groq real: no se sabe si acepta `reasoning_effort` con cada modelo ni cómo continúa un texto cortado.

## Se quita la sorpresa del 67 (revisión 15)
- Eliminada la sorpresa del «67»: ya no hay robot, ni respuesta «SIX SEVEEEEEEEEEEEEEEEN», ni detección en `huevos.ts`, `Huevo.tsx` ni `dominio/sorpresas.py`. Escribir 67 vuelve a ser un mensaje normal (ModeloReglas responde «No estoy seguro…»). La sorpresa de «Fernando Alonso» (animación y foto) no se ha tocado. `frontend/dist` reconstruido; tests ajustados (90 de Python pasan; los de vitest no se han podido ejecutar aquí).

## Colores azul/violeta, respuestas sin asteriscos y menús a 1080 (revisión 16)
- Todos los amarillos/ámbar (variables `--ambar`→`--acento`, esfera, logo, icono, scroll, trofeo) pasan a azul y violeta; paleta inspirada en neón cyberpunk (cian `#00f3ff`, azul `#0080ff`, violeta `#8b5cf6`). No se añade ninguna librería externa.
- Las respuestas de NEXO se pintan con su Markdown resuelto (`src/formato.ts`, `TextoFormateado.tsx`): negrita, cursiva, listas y títulos sin asteriscos; «3 * 79,9» conserva el `*`. «Copiar» entrega texto limpio. Además el modelo LLM recibe la instrucción de escribir en texto plano.
- Menús rehechos para que a 1920x1080 todo quepa sin scroll de página (barra lateral de 248 px, paneles de 320 px, estadísticas en 3 columnas, ayuda de teclado bajo el compositor).
- Media queries reunidas en `src/estilos/responsive.css` (se carga la última): cajón lateral en pantallas estrechas o bajas, paneles a pantalla completa en móvil, esfera más baja en alturas ≤800 px. Revisado con Chrome a 1920x1080, 1366x768, 1280x720, 1024x768, 768x1024, 390x844, 360x640 y 844x390. Quedan copias antiguas de `@media` en otros `.css` (inocuas: `responsive.css` gana por cascada).
- Pendiente de ver: el panel Configuración sigue con scroll interno por debajo de 1080 px de alto.

## Documentación al día (revisión 17)
- Revisados contra el código `README.md`, `GUIA_FUNCIONAMIENTO.md`, `Referencias.md` y `docs/*.md`: estructura de carpetas (`probar_llm.py`, `ejecutar_tests.py`, `.env.example`, `sorpresas.py`, `formato.ts`, `responsive.css`), instalación y arranque (venv, `pip install -r requirements.txt`, `python main_web.py`, `.env` desde `.env.example`), tabla de variables `LLM_*`, recuento de tests (120 funciones `test_*` en Python; 90 sin FastAPI; unos 35 casos de vitest), sorpresas, paleta azul/violeta y contratos de error de la API.
- Las capturas de `docs/` se han rehecho con la paleta azul/violeta.
- Informes históricos (`docs/AUDITORIA.md`, `docs/INFORME_REDISENO.md`) llevan una nota de que son de revisiones anteriores.
