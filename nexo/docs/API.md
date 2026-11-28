# Contratos de la API de NEXO

Base: `http://127.0.0.1:8000/api` · JSON · documentación interactiva en `/api/docs`.

## Errores

Todos los errores usan el mismo formato: `{"error": {"codigo": "...", "mensaje": "..."}}`.

| HTTP | `codigo` | Cuándo |
|---|---|---|
| 404 | `conversacion_no_encontrada` | El id no existe o no es válido |
| 404 / 405 | `no_encontrado` / `metodo_no_permitido` | Ruta inexistente o método incorrecto |
| 409 | `limite_contexto` | El mensaje haría superar el límite de tokens de la conversación (no se añade) |
| 422 | `peticion_invalida` | Cuerpo no válido (vacío, > 2000 caracteres, campos extra…) |
| 422 | `modelo_no_disponible` | Modelo inexistente o no disponible (p. ej. `llm` sin `LLM_API_KEY`) |
| 422 | `argumentos_invalidos` | Argumentos de herramienta no válidos |
| 502 | `error_proveedor` | El proveedor LLM rechazó o no pudo completar la petición. El `mensaje` incluye el código HTTP y el motivo del proveedor (clave inválida, modelo inexistente, límite...), nunca la clave |
| 500 | `error_almacenamiento` · `herramienta_no_encontrada` · `error_interno` | Fallo interno; mensaje genérico |

## Endpoints

| Método y ruta | Cuerpo | Respuesta |
|---|---|---|
| `GET /salud` | | `{"estado": "ok"}` |
| `GET /modelos` | | Catálogo completo, locales primero y remoto después (ver abajo) |
| `GET /herramientas` | | `[{"nombre", "descripcion", "parametros"}]` |
| `GET /estadisticas` | | `{conversaciones, peticiones, tokens_entrada_estimados, tokens_salida_estimados, tokens_salida_llm, coste_eur, nota, herramientas: {nombre: {usos, fallos}}}` |
| `GET /conversaciones` | | `[{"id", "titulo", "mensajes", "actualizada"}]`, la más reciente primero |
| `POST /conversaciones` | | `201` · conversación nueva (en memoria hasta su primer mensaje) |
| `GET /conversaciones/{id}` | | Conversación |
| `PATCH /conversaciones/{id}` | `{"modelo": "eco"}` | Conversación |
| `POST /conversaciones/{id}/mensajes` | `{"texto": "..."}` | `{"respuesta", "herramientas_usadas": [{"nombre", "argumentos"}], "conversacion"}` |
| `POST /conversaciones/{id}/mensajes/stream` | `{"texto": "..."}` | `text/event-stream` (abajo) |

**Modelos:** `GET /modelos` devuelve siempre las tres opciones (`reglas`, `eco`, `llm`), esté o no configurada `LLM_API_KEY`. Cada entrada es `{"id", "nombre", "tipo": "local"|"remoto", "disponible": bool, "motivo": str|null, "detalle": str|null}`:

```json
[
  {"id": "reglas", "nombre": "ModeloReglas", "tipo": "local",  "disponible": true,  "motivo": null, "detalle": null},
  {"id": "eco",    "nombre": "ModeloEco",    "tipo": "local",  "disponible": true,  "motivo": null, "detalle": null},
  {"id": "llm",    "nombre": "ModeloLLM",    "tipo": "remoto", "disponible": true,  "motivo": null, "detalle": "openai/gpt-oss-120b"}
]
```

Con clave, `detalle` es el nombre del modelo del proveedor (`LLM_MODEL`). Sin clave, `llm` sale con `"disponible": false`, `"motivo": "Configura LLM_API_KEY en el archivo .env del servidor."` y `"detalle": null`. Cambiar a un modelo no disponible (`PATCH /conversaciones/{id}`) devuelve `422` con código `modelo_no_disponible` y el motivo en el mensaje; la clave nunca se expone.

**Conversación:** `{"id", "modelo", "mensajes": [{"rol", "contenido", "fecha"}], "tokens_estimados", "limite_tokens"}`. Roles: `usuario`, `asistente`, `herramienta` (contenido `[nombre] resultado`).

## Streaming (SSE)

| Evento | `data` |
|---|---|
| `herramienta` | `{"tipo", "nombre", "argumentos", "resultado", "error"}`, uno por herramienta ejecutada |
| `fragmento` | `{"texto": "..."}`, parte de la respuesta final |
| `fin` | Conversación completa y guardada |
| `error` | `{"codigo", "mensaje"}`; los errores anteriores al inicio del flujo (404, 422) son HTTP normales |

Los fragmentos de `ModeloReglas` son una entrega progresiva de un texto ya completo. `ModeloLLM` los transmite a medida que llegan desde el proveedor. El modelo remoto solo se puede usar si `LLM_API_KEY` está configurada en el servidor; si no, aparece en `GET /modelos` como no disponible.
