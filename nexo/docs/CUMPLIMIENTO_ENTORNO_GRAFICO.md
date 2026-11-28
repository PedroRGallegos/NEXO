# Cumplimiento del enunciado en el entorno gráfico

Fecha: 27 de noviembre de 2026

Interpreto «solo y únicamente entorno gráfico» así: el producto se entrega y se usa por la interfaz web, y cada función que el enunciado pide en la consola debe poder hacerse desde ella. Si lo entendías de otra forma, dímelo.

Este repaso es por lectura de código y por pruebas en navegador con una API simulada. No he ejecutado la suite de Python ni el servidor real (faltan dependencias en mi entorno), y eso no cubre el cumplimiento de la parte de backend.

## 1. Comandos de la consola y su equivalente gráfico

| Comando del enunciado | Equivalente en la interfaz | Estado |
|---|---|---|
| Texto normal | Campo de comandos del chat, con respuesta en streaming | Cubierto |
| Llamada a herramienta (`🔧 calculadora(a=3, b=79.9, operacion='*')`) | Línea «⚙ calculadora (a=3, b=79.9, operacion='*')» con su resultado | **Corregido en esta revisión**: antes solo se veía el resultado |
| `/herramientas` | Panel Configuración, lista de herramientas | Cubierto |
| `/modelo eco · reglas` | Panel Configuración, selector de modelo en caliente | Cubierto; **ahora con aviso «Modelo cambiado a …»** |
| `/historial` (mensajes y tokens estimados) | Mensajes en pantalla, medidor «contexto» y HUD con tokens estimados | Cubierto |
| `/guardar` | Guardado automático tras cada respuesta; la cabecera muestra «sesión <id> · guardada» | **Añadido**: el enunciado pide confirmar el guardado con su id |
| `/cargar <id>` · `/lista` | Historial de la barra lateral | Cubierto |
| `/nueva` | Botón «Nueva conversación» | Cubierto |
| `/stats` | Panel Estadísticas (peticiones, tokens, coste, uso y fallos por herramienta) | Cubierto |
| `/salir` | No aplica en una web | No aplica |
| Errores amables sin cerrar el programa | Banner de error descartable; la interfaz sigue funcionando | Cubierto |

## 2. Añadido del segundo enunciado (relacionado con la interfaz)

| Requisito | En la interfaz | Estado |
|---|---|---|
| Streaming por fragmentos | El texto aparece mientras llega, con cursor | Cubierto en la interfaz; el modelo LLM real nunca se ha probado |
| Validar la petición antes de enviar | Lo hace el backend (`validar()`); un error llega como mensaje amable | Backend (no ejecutado aquí) |
| Reintentos con `tenacity` (5 intentos, espera exponencial) | Backend, `dominio/modelos.py` | Backend (no ejecutado aquí) |
| Clave en `.env` y `.gitignore` | `.env.example` con `LLM_API_KEY`; `.env` está en `.gitignore`; el panel avisa de que la clave vive en el servidor | Cubierto |
| Registro de tokens y coste en `uso.csv` | Panel Estadísticas: tokens y coste | Cubierto (coste con tarifa configurable, estimado) |
| `ModeloReglas` frente a `ModeloLLM` | Ambos aparecen en el selector; `ModeloLLM` sale desactivado («NO CONFIGURADO») si no hay clave | Cubierto |

## 3. Lo que queda fuera del entorno gráfico

- El script de comparación de 10 preguntas, las 5 conclusiones y el cuaderno del Tema 2 no son una función de la interfaz. Siguen pendientes si los necesitas para la entrega.
- Los tests de `unittest` del enunciado nuevo (mensaje vacío, CSV, 429) pertenecen al backend.

## 4. Limitaciones conocidas

- Los argumentos de las herramientas se ven mientras se responde y durante la sesión. Si recargas la página o abres una conversación antigua, solo aparece el resultado, porque el servidor guarda únicamente «[herramienta] resultado». Persistirlos exigiría cambiar el backend.
- El aspecto en móvil y en distintos tamaños se revisó con Chrome tras el rediseño responsive (ver `CAMBIOS.md`, revisión 16); el panel Configuración sigue con scroll interno por debajo de 1080 px de alto.
