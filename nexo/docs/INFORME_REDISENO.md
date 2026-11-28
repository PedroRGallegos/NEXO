# Informe de rediseño, optimización y limpieza de NEXO

> **Nota (27/11/2026):** documento histórico de una revisión anterior. Desde entonces la paleta pasó de ámbar a azul y violeta, la sorpresa del «67» se eliminó (solo queda «Fernando Alonso») y hay más tests. El estado actual está en `README.md`, `CAMBIOS.md` (revisiones 14 a 17) y `docs/PRUEBAS.md`.

Fecha: 27 de noviembre de 2026

## 1. Resumen de la auditoría inicial

La auditoría fue por lectura de código; no se ejecutó la suite de Python (faltan `httpx`, `tenacity` y `fastapi` en el entorno).

- Los niveles 1 y 2 del enunciado y los 6 retos del nivel 3 tienen evidencia en el código (21 requisitos con fichero que los demuestra).
- Parcial: el CSV `uso.csv` tiene un esquema mixto de 9 columnas, distinto de la cabecera del enunciado.
- El reto 2 (`ModeloLLM`) existe pero nunca se ha probado contra un proveedor real.
- Alcance extra, no exigido por el enunciado: API FastAPI, gestor de conversaciones, paneles, logo, esfera y easter eggs.
- Hallazgos: unas 30 clases CSS sin uso del núcleo antiguo, datos simulados presentados como lecturas reales en el HUD, un comentario falso en `requirements.txt`, un endpoint no streaming que solo usan los tests.

El informe completo de la auditoría está en `docs/AUDITORIA.md`.

## 2. Requisitos del enunciado (resumen)

| Bloque | Requisitos |
|---|---|
| Nivel 1 (núcleo) | 4 capas y `main.py`; 3 herramientas con herencia; 2 modelos intercambiables; mensajes privados con copia; agente polimórfico; excepciones propias; sin `print`/`input` en dominio y servicios; `Mensaje`, `Conversacion` y `Respuesta`; bucle de máximo 3 vueltas |
| Nivel 2 | Repositorio JSON; registro CSV con `resumen()`; comandos de la consola |
| Nivel 3 | Herramienta nueva sin tocar el agente; `ModeloLLM`; `esquema()`; varias herramientas por pregunta; tests; resumen automático al 80 % |
| Entrega | README con ejecución, nivel y retos; diagrama de clases; uso de la IA; reflexión; zip sin `.venv` |

## 3. Tres alternativas visuales

| Propuesta | Claridad | Rendimiento | Complejidad | Mantenimiento |
|---|---|---|---|---|
| Cyberpunk completa | Media: mucho adorno | Peor: esfera continua y capas de pantalla completa | Alta | Media |
| Minimalista profesional | Alta | Mejor | Baja | Alta |
| **Híbrida (elegida)** | Alta | Buena | Media | Alta |

**Decisión:** híbrida. Se conserva la identidad cyberpunk (paleta ámbar, cian y magenta, bordes biselados, logo y esfera), pero cada elemento debe aportar información real. Ofrece la mejor relación entre claridad y personalidad, y no obliga a tocar el backend.

## 4. Arquitectura final

- Backend sin cambios de arquitectura: `dominio/`, `servicios/`, `persistencia/`, `presentacion/`, `main.py` y `main_web.py`.
- Frontend React + TypeScript: `api/` (cliente y SSE), `hooks/useChat.ts`, `components/`, `estilos/` y `huevos.ts`.
- Estilos en capas: `base`, `layout`, `componentes`, `cyberpunk` (identidad), `logo` y `esfera`.
- Easter eggs: registro en `huevos.ts` (lógica sin React) más ilustraciones en `components/Huevo.tsx`.

## 5. Cambios en frontend y backend

Frontend:
- El HUD de la esfera muestra solo datos reales: modelo, contexto estimado, estado, último comando y estado de la API.
- La esfera limita sus fotogramas: 20 por segundo en reposo y 30 con actividad.
- Se retiran las capas de pantalla completa (líneas de barrido y viñeta).
- Correcciones de revisiones anteriores: conversación equivocada al cambiar durante una respuesta, parser SSE con CRLF, temporizador de «copiar».

Backend:
- `PeticionInvalida` responde 422 en lugar de un 500 genérico.
- Se corrige el comentario falso de `requirements.txt`.

## 6. Eliminado y justificación

| Elemento | Justificación |
|---|---|
| 81 selectores CSS sin referencia en el código (núcleo antiguo de `NexoFace`, `marca__logo`, `bienvenida__glifo`) | Sin uso comprobado por script |
| Número de «carga del sistema» aleatorio, «218 Hz», «MALLA 1700 PTS», «RADIO/ESCALA», «SEÑAL ESTABLE», «ENLACE LOCAL · ACTIVO» fijo | Eran datos inventados presentados como lecturas |
| Capas `body::before` y `body::after` | Decorativas; no se pudo demostrar su coste, pero no aportan información |
| Intervalo de 1,8 s que forzaba re-renders del HUD | Existía solo para el número aleatorio |
| `node_modules/` y `datos/` del zip | Binarios de Windows y datos generados |

**No eliminado:** el endpoint `POST /mensajes` sin streaming. Solo lo usan los tests y `docs/API.md`; borrarlo sin poder ejecutar la suite de Python arriesgaba romper algo. Queda como mejora pendiente.

## 7. Rendimiento: antes y después

Medidas en Chromium sin GPU, una sola ejecución cada una, con API simulada. Son orientativas.

| Métrica | Antes | Después |
|---|---|---|
| `index.js` | 258.083 B (80.542 B gzip) | 256.585 B (80.492 B gzip) |
| `index.css` | 40.596 B (8.983 B gzip) | 31.050 B (7.155 B gzip) |
| Script por segundo en reposo | 14,8 ms | 22,9 ms |
| CPU de tareas por segundo en reposo | 190,6 ms | 208,5 ms |

**Lectura honesta:** el CSS baja un 24 % en bytes y un 20 % comprimido, y el JS apenas cambia. En CPU **no se demuestra mejora**: las cifras de después salieron algo mayores, pero los métodos de medición no son idénticos y una ejecución sola es ruido. El heap (9,54 MB antes y 4,59 MB después) y los nodos DOM no son comparables porque se midieron de forma distinta. No afirmo que haya mejoras de CPU o memoria.

## 8. Easter egg «Fernando Alonso»

- Detección con la expresión completa «fernando alonso», sin distinguir mayúsculas ni tildes y con límites de palabra: se activa dentro de una frase («viva Fernando Alonso hoy») y no en «fernandoalonso» ni con «alonso» suelto.
- Se muestra el nombre correctamente escrito, «Fernando Alonso», con independencia de cómo se haya tecleado.
- **Limitación deliberada:** no se dibuja a Fernando Alonso ni se usan fotos suyas, porque es una persona real. La ilustración es un piloto genérico original que celebra con un trofeo y confeti.
- Se activa una vez por envío, no en cada renderizado, y no interfiere con el envío del mensaje: el servidor recibió los 6 mensajes de prueba.
- El registro `huevos.ts` permite añadir otros easter eggs sin tocar la lógica del chat.
- Se mantiene también el robot original del «67».

## 9. Tests ejecutados

- `tsc --noEmit`: sin errores.
- Lógica en Node (con un sustituto mínimo de `vitest`): 4 tests de SSE y 5 de detección, todos correctos.
- Navegador (Chromium, API simulada): 6 casos de easter egg correctos, 6 mensajes enviados y sin errores de consola.
- **No ejecutado:** la suite de Python (faltan dependencias), `vitest` y `vite` reales (falta el binario de rollup para Linux), el servidor real y cualquier proveedor LLM. `dist` se compiló con esbuild.

## 10. Pendiente y mejoras futuras

- Ejecutar `pytest`, `npm test` y `npm run build` en una máquina con las dependencias.
- Decidir si se elimina el endpoint no streaming y se actualizan tests y `docs/API.md`.
- `GestorConversaciones` guarda agentes en memoria sin límite; `_estadisticas` relee el disco en cada petición.
- Alinear `uso.csv` con la cabecera del enunciado.
- Revisar `README.md`, `GUIA_FUNCIONAMIENTO.md`, `INFORME.md` y `CAMBIOS.md`: no se ha comprobado que estén al día.
- Comprobar el aspecto en móvil y en pantallas con GPU.
- Probar `ModeloLLM` contra un proveedor real.

## Subagentes

Se usaron dos subagentes reales, de solo lectura: **A (auditoría)** y **C (rendimiento, línea base)**. Los trabajos de diseño, limpieza, backend y validación los hice yo directamente, sin subagentes independientes, y no hubo ningún agente de validación separado.
