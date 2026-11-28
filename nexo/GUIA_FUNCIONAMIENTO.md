# Guía breve de funcionamiento de NEXO

Este documento resume el funcionamiento del programa para explicar qué hace, cómo responde y cuáles son sus límites.

## ¿Qué es NEXO?

NEXO es un asistente de TechNova con una interfaz web visual y una consola local para desarrollo. Puede funcionar sin conexión con `ModeloReglas` y `ModeloEco`; al configurar `LLM_API_KEY` en el servidor web, también puede usar un proveedor compatible con Chat Completions (OpenAI, o Groq con `LLM_API_URL` y `LLM_MODEL` del `.env`).

## ¿Qué ocurre cuando se hace una pregunta?

1. `ChatConsola` recibe el texto escrito y se lo pasa al `Agente`.
2. El agente lo añade a la conversación y pide una decisión al modelo activo.
3. El modelo devuelve una respuesta escrita o solicita una herramienta con sus argumentos.
4. Si se solicitó una herramienta, el agente la busca y la ejecuta. Añade el resultado a la conversación y vuelve a consultar el modelo para que formule la respuesta final.
5. El agente permite hasta tres vueltas de solicitud de herramientas por mensaje. La presentación muestra las herramientas usadas y la respuesta.

El modelo solo solicita la herramienta: **quien la ejecuta es el agente**. Así, la ejecución y el registro quedan bajo el control del programa.

## Modelos y herramientas

- **`ModeloReglas`** reconoce patrones sencillos en el último mensaje: operaciones aritméticas, conversiones de moneda, preguntas frecuentes, hora/fecha, consultas de stock y saludos. Si no reconoce la petición, solicita que se reformule.
- **`ModeloEco`** repite el último mensaje del usuario; sirve para comprobar el flujo básico.
- **`ModeloLLM`** transmite texto del proveedor en tiempo real y puede pedir una herramienta registrada. Solo está disponible en la web si el servidor tiene `LLM_API_KEY` (si no, aparece desactivado). Si la respuesta se corta en `LLM_MAX_TOKENS`, continúa hasta `LLM_MAX_TOKENS_AMPLIADO`. Si el proveedor rechaza la petición, se muestra su motivo (código HTTP y mensaje, nunca la clave).
- **`calculadora`** suma, resta, multiplica o divide dos números.
- **`conversor_moneda`** convierte entre EUR, USD, GBP y JPY con tasas fijas definidas en el código; no consulta cotizaciones actuales.
- **`buscador_faq`** elige una respuesta de una FAQ fija según las palabras compartidas con la pregunta.
- **`consulta_stock`** busca productos en un catálogo de existencias fijo en el código.
- **`reloj`** proporciona la fecha y hora del sistema.

`ModeloReglas` puede encadenar una conversión de moneda con una operación aritmética. La FAQ y el catálogo usan coincidencia de palabras, no comprensión semántica; por eso pueden no encontrar una respuesta aunque la pregunta sea razonable.

## Conversación y memoria

Una conversación contiene mensajes de usuario, asistente y herramientas. El historial se guarda como JSON al ejecutar `/guardar` en la consola; en la web se guarda automáticamente tras cada respuesta. Cada conversación tiene un identificador. `uso.csv` registra el uso de herramientas y, para llamadas LLM, timestamp, pregunta, tokens reales de salida y coste estimado según la tarifa configurada.

El límite predeterminado es de 500 tokens estimados (el programa aproxima 1,3 tokens por palabra). Al superar el 80 % del límite, el agente sustituye los mensajes antiguos por un resumen extractivo breve y conserva intacto el intercambio actual. No es un resumen generado por IA.

## Capas del programa

- `presentacion/`: chat por consola, comandos y mensajes mostrados; no implementa la lógica de negocio.
- `servicios/`: `Agente`, que coordina modelo, conversación, herramientas y registro.
- `dominio/`: mensajes, conversación, modelos, herramientas y errores.
- `persistencia/`: guardado/carga de conversaciones JSON y registro CSV.
- `main.py`: crea las instancias y conecta las capas.

## Comandos principales

| Comando | Función |
| --- | --- |
| `/herramientas` y `/esquemas` | Lista las herramientas o muestra sus esquemas JSON. |
| `/modelo eco` y `/modelo reglas` | Cambia el modelo activo. |
| `/historial` | Muestra los mensajes y los tokens estimados. |
| `/guardar`, `/cargar <id>` y `/lista` | Guarda, carga o lista conversaciones. |
| `/nueva` | Empieza una conversación vacía. |
| `/limpiar` | Guarda la conversación y empieza de cero; la anterior se recupera con `/cargar <id>`. |
| `/stats` | Resume los usos y fallos registrados por herramienta. |
| `/ayuda` y `/salir` | Muestra los comandos o termina el chat. |

## Errores y límites

Los argumentos inválidos de una herramienta se añaden al historial como un resultado de error para que el modelo pueda responder. Un nombre de herramienta inexistente genera un error del agente. Si se rebasa el límite de contexto, el mensaje no se añade y el chat recomienda empezar otra conversación. El lenguaje entendido por `ModeloReglas`, las respuestas de la FAQ, el inventario y los tipos de cambio son deliberadamente limitados y fijos.

## Interfaz web

`python main_web.py` arranca una API (FastAPI) que reutiliza el mismo `Agente` mediante el `GestorConversaciones` (un agente por conversación) y sirve el frontend React. El usuario desplegado interactúa únicamente con esta interfaz; la API mantiene la clave del proveedor en el servidor. El frontend solo envía mensajes y muestra lo que devuelve la API; toda la lógica sigue en las capas inferiores. Más detalle en la sección 10 del README.

Equivalencias entre los comandos de la consola y la interfaz:

| Consola | Interfaz web |
| --- | --- |
| Texto normal | Campo de comandos del chat, con la respuesta en streaming |
| `/herramientas` | Panel Configuración |
| `/modelo eco` y `/modelo reglas` | Selector de modelo del panel Configuración, con aviso al cambiar. ModeloLLM aparece en un grupo aparte, desactivado si falta `LLM_API_KEY` |
| `/historial` | Mensajes en pantalla, medidor de contexto y panel de datos del núcleo |
| `/guardar` | Guardado automático; la cabecera muestra «sesión <id> · guardada» |
| `/cargar <id>` y `/lista` | Historial de la barra lateral |
| `/nueva` | Botón «Nueva conversación» |
| `/limpiar` (o `/clear`) | Se escribe en el chat: deja la conversación en blanco y la anterior sigue en el historial. |
| `/stats` | Panel Estadísticas |
| `/salir` | No aplica en una web |

La esfera del centro refleja el estado del agente: en espera, procesando (mientras decide o ejecuta una herramienta) o respondiendo (mientras llega el texto). Los datos que la rodean son reales: modelo, tokens estimados, estado de la API y último comando. Al enviar «Fernando Alonso» aparece además una animación de sorpresa con un piloto genérico original, y `ModeloReglas` contesta con una foto; no afecta al envío del mensaje. Las respuestas del modelo se muestran con su Markdown resuelto (negrita, listas y títulos, sin asteriscos sueltos). La paleta es cian, azul y violeta, y los menús se adaptan a pantallas pequeñas.

## Ejecución y pruebas

Desde la carpeta del proyecto:

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py                                       # consola
python main_web.py                                   # web: http://127.0.0.1:8000
python -m unittest discover -s tests -t .            # tests de Python (o: python ejecutar_tests.py)
```

Los tests del frontend se ejecutan con `npm test` dentro de `frontend/` (tras `npm install`). Las dependencias de `requirements.txt` hacen falta también para la consola.

Para usar el proveedor remoto, copia `.env.example` a `.env`, establece `LLM_API_KEY` y ajusta `LLM_API_URL`, `LLM_MODEL` y la tarifa real del modelo en `LLM_COST_PER_1K_OUTPUT`. Otras variables: `LLM_MAX_TOKENS` (500), `LLM_MAX_TOKENS_AMPLIADO` (1000), `LLM_REASONING_EFFORT`, `LLM_SYSTEM` y `LLM_TEMPERATURE` (tabla completa en la sección 10 del README). `python probar_llm.py` comprueba la configuración con una llamada real.
