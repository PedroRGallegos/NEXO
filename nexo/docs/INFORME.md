# Informe de limpieza, pruebas y pendientes

## 1. Estado de partida (auditoría)

El proyecto recibido (`RodriguezSanchezNEXO`) tenía completos los niveles 1 y 2 y los retos 1, 3, 4, 5 y 6 del nivel 3, con 56 tests en verde. **No tenía** capa web, frontend, LLM real, streaming ni registro de tokens/costes (el `uso.csv` original registra herramientas, no tokens).

| Área | Estado inicial | Acción |
|---|---|---|
| Dominio, agente, persistencia, consola | Completo y verificado (56 tests) | Se conserva sin cambiar firmas públicas |
| Interfaz gráfica / comunicación API | Inexistente | Creados: API FastAPI + frontend React |
| Streaming | Inexistente | SSE por pasos del agente |
| Modelo LLM, reintentos, temperature/max_tokens, costes | Inexistente | `ModeloLLM` opcional con clave en `.env`, validación, reintentos, streaming real y CSV |
| Seguridad | Id de conversación validado; sin superficie de red | Validación y errores de la API |

## 2. Limpieza y refactorización

| Elemento | Problema | Acción |
|---|---|---|
| `RodriguezSanchezNEXO.zip` dentro del ZIP recibido | Copia duplicada del proyecto | Eliminado del árbol de trabajo (no se entrega) |
| `tests/test_dominio.py`, `test_mejoras.py`, `test_agente_y_persistencia.py` | Import sin usar (`Respuesta`, `ErrorPersistencia`) y variable `tmp` sin usar | Eliminados (pyflakes sin avisos) |
| `Agente.procesar()` | Un streaming por pasos habría duplicado el bucle | El bucle vive en `procesar_por_pasos()`; `procesar()` lo consume |
| `main.py` | Lista de herramientas repetible en el punto de entrada web | Extraída a `construir_herramientas()` (consola y web la comparten) |
| `.gitignore`, `requirements*.txt` | No existían | Creados |

Código muerto, duplicado o dependencias sobrantes: no se han encontrado más (pyflakes limpio; el proyecto original no tenía dependencias).

## 3. Pruebas

| Prueba | Resultado |
|---|---|
| Python: dominio, API, persistencia, LLM, reintentos y streaming (proveedor simulado) | 120 funciones `test_*`; 90 pasan sin FastAPI (sin `test_api.py` ni `test_modelo_llm.py`) |
| Frontend: SSE, formato Markdown, sorpresas, voz, comandos, imágenes y modelos (vitest) | unos 35 casos (recuento estático); no ejecutados en el entorno de desarrollo |
| `npm run build` (TypeScript estricto) | OK |
| Prueba manual web: API de salud, frontend servido, chat y SSE | OK; NEXO respondió y cambió a estado «hablando» |

No probado: proveedor externo con clave facturable, lectores de pantalla, carga con muchos mensajes, concurrencia real ni navegadores adicionales.

## 4. Pendiente y limitaciones

- **LLM real (`ModeloLLM`):** opcional; requiere una clave de API válida en el servidor. Las pruebas usan un transporte HTTP simulado y no validan facturación ni disponibilidad real del proveedor.
- **Tokens:** son estimaciones (palabras × 1,3) y se calculan sobre el historial guardado, que tras un resumen automático es más corto que el real.
- **Streaming local:** entrega progresiva de un texto ya completo (el modelo de reglas no genera token a token). El LLM transmite los fragmentos del proveedor.
- **Seguridad:** sin autenticación ni límite de peticiones; pensada para `127.0.0.1`.
- **Persistencia:** el modelo elegido y el límite de tokens no se guardan con la conversación.
- **Git:** el ZIP no incluía `.git`; no se ha podido revisar el historial ni se ha hecho ningún commit.
- **README:** las secciones `[COMPLETAR]` del apartado 8 (uso de la IA) deben rellenarlas las personas autoras.
