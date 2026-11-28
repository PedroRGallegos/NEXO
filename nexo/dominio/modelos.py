"""Modelos: deciden si responder directamente o pedir que se ejecute una herramienta.

Es el mecanismo de *tool calling* de las APIs reales (OpenAI, Anthropic, Gemini):
el modelo NO ejecuta nada, solo pide que se ejecute una herramienta.
"""

import json
import os
import re
from collections.abc import Callable, Iterator

import httpx
from dotenv import load_dotenv
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from dominio.excepciones import ErrorProveedorLLM
from dominio.herramientas import NO_ENCONTRADO
from dominio.mensaje import PREFIJO_RESUMEN, Conversacion
from dominio.sorpresas import respuesta_sorpresa
from dominio.texto import normalizar

load_dotenv()


class PeticionInvalida(ValueError):
    """La configuración o el historial no cumplen el contrato del proveedor."""


def validar(mensajes: list[dict], max_tokens: int, temperature: float) -> None:
    """Valida el formato y los parámetros antes de enviar una petición al proveedor."""
    if not mensajes or not isinstance(mensajes[0], dict) or mensajes[0].get("role") != "user":
        raise PeticionInvalida("El primer mensaje debe tener el rol 'user'.")
    roles_validos = {"system", "user", "assistant", "tool"}
    for mensaje in mensajes:
        if not isinstance(mensaje, dict) or mensaje.get("role") not in roles_validos:
            raise PeticionInvalida("La petición contiene un rol no válido.")
        if not isinstance(mensaje.get("content"), str):
            raise PeticionInvalida("El contenido de cada mensaje debe ser texto.")
    if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens <= 0:
        raise PeticionInvalida("max_tokens debe ser un entero mayor que cero.")
    if (
        isinstance(temperature, bool)
        or not isinstance(temperature, (int, float))
        or not 0 <= temperature <= 2
    ):
        raise PeticionInvalida("temperature debe estar en el rango [0, 2].")


def _es_error_reintentable(error: BaseException) -> bool:
    if not isinstance(error, httpx.HTTPStatusError):
        return False
    estado = error.response.status_code
    return estado == 429 or 500 <= estado < 600


INSTRUCCION_LLM = (
    "Responde en español, de forma clara y completa pero concisa: que toda la respuesta quepa "
    "en unas 250 palabras y termina siempre con una frase completa. No empieces con rodeos. "
    "Escribe en texto plano: sin Markdown, sin asteriscos ni almohadillas; para enumerar usa líneas que empiecen por un guion."
)


def _detalle_error_proveedor(respuesta: httpx.Response) -> str:
    """Motivo que da el proveedor (OpenAI, Groq...) en su JSON de error, si lo hay."""
    try:
        cuerpo = respuesta.json()
        error = cuerpo.get("error") if isinstance(cuerpo, dict) else None
        mensaje = error.get("message") if isinstance(error, dict) else error
    except (ValueError, httpx.ResponseNotRead):
        return ""
    if not isinstance(mensaje, str) or not mensaje.strip():
        return ""
    return f" Motivo: {mensaje.strip()[:300]}"


def _tokens_de_uso(fragmento: dict) -> int | None:
    """completion_tokens del fragmento: OpenAI lo da en 'usage'; Groq también en 'x_groq.usage'."""
    candidatos = [fragmento.get("usage")]
    x_groq = fragmento.get("x_groq")
    if isinstance(x_groq, dict):
        candidatos.append(x_groq.get("usage"))
    for uso in candidatos:
        if isinstance(uso, dict) and isinstance(uso.get("completion_tokens"), int):
            return uso["completion_tokens"]
    return None


class Respuesta:
    """Resultado de un modelo: o bien un texto final, o bien la petición de una herramienta."""

    def __init__(self, texto=None, herramienta=None, argumentos=None):
        self.texto = texto  # Respuesta final para el usuario
        self.herramienta = herramienta  # O bien: nombre de la herramienta a usar
        self.argumentos = argumentos or {}

    def es_llamada_herramienta(self) -> bool:
        return self.herramienta is not None

    def __repr__(self) -> str:
        if self.es_llamada_herramienta():
            return f"Respuesta(herramienta={self.herramienta!r}, argumentos={self.argumentos!r})"
        return f"Respuesta(texto={self.texto!r})"


class Modelo:
    """Clase base de todos los modelos."""

    remoto = False  # True si responde a través de un servicio externo

    def __init__(self, nombre: str):
        self.nombre = nombre

    def responder(self, conversacion: Conversacion, herramientas: list) -> Respuesta:
        raise NotImplementedError("Cada modelo debe implementar responder()")

    def responder_por_fragmentos(self, conversacion: Conversacion, herramientas: list) -> Iterator[dict]:
        """Devuelve una respuesta completa; los modelos remotos pueden emitir fragmentos."""
        yield {"tipo": "respuesta", "respuesta": self.responder(conversacion, herramientas)}

    def __str__(self) -> str:
        return self.nombre


class ModeloEco(Modelo):
    """Repite el último mensaje del usuario. Sirve para comprobar que todo encaja."""

    def __init__(self):
        super().__init__("ModeloEco")

    def responder(self, conversacion: Conversacion, herramientas: list) -> Respuesta:
        for mensaje in reversed(conversacion.get_mensajes()):
            if mensaje.rol == "usuario":
                return Respuesta(texto=f"Has dicho: {mensaje.contenido}")
        return Respuesta(texto="No hay nada que repetir todavía.")


def _a_numero(texto: str) -> int | float:
    """'3' -> 3, '79,9' -> 79.9."""
    numero = float(texto.replace(",", "."))
    return int(numero) if numero.is_integer() else numero


class ModeloReglas(Modelo):
    """Modelo basado en reglas: mira el último mensaje y decide qué hacer."""

    _NUMERO = r"(\d+(?:[.,]\d+)?)"
    _PATRON_OPERACION = re.compile(r"(\d+[.,]?\d*)\s*([+\-*/x])\s*(\d+[.,]?\d*)", re.IGNORECASE)
    _PATRON_NUMERO = re.compile(_NUMERO)
    _PATRON_MONEDA = re.compile(r"\b(usd|gbp|jpy|eur|dolar(?:es)?|libras?|yen(?:es)?|euros?)\b")
    _PATRON_FAQ = re.compile(r"\b(envio|devol\w*|horario|pago)")
    _PATRON_RELOJ = re.compile(r"\b(que hora es|que hora son|la hora actual|la fecha|que dia es|que fecha)\b")
    _PATRON_STOCK = re.compile(r"\b(stock|quedan|queda|disponibles?|disponibilidad|unidades)\b")
    _PATRON_SALUDO = re.compile(
        r"\b(hola|buenas|buenos dias|buenas tardes|buenas noches|hey|ey|saludos)\b"
    )
    _CODIGO_MONEDA = {
        "usd": "USD", "dolar": "USD", "dolares": "USD",
        "gbp": "GBP", "libra": "GBP", "libras": "GBP",
        "jpy": "JPY", "yen": "JPY", "yenes": "JPY",
        "eur": "EUR", "euro": "EUR", "euros": "EUR",
    }
    _MONEDAS_QUE_ACTIVAN = {"USD", "GBP", "JPY"}
    # Peticiones encadenadas: "convierte 100 USD a euros y multiplícalo por 3"
    _CALCULO_ENCADENADO = (
        (re.compile(r"\bmultiplic\w*\s+(?:por\s+)?" + _NUMERO), "*"),
        (re.compile(r"\bdivid\w*\s+(?:entre|por)\s+" + _NUMERO), "/"),
        (re.compile(r"\bsum\w*\s+" + _NUMERO), "+"),
        (re.compile(r"\brest\w*\s+" + _NUMERO), "-"),
    )
    _PATRON_IMPORTE_CONVERTIDO = re.compile(r"=\s*(\d+(?:\.\d+)?)")

    def __init__(self):
        super().__init__("ModeloReglas")

    def responder(self, conversacion: Conversacion, herramientas: list) -> Respuesta:
        mensajes = conversacion.get_mensajes()
        if not mensajes:
            return Respuesta(texto="No estoy seguro, ¿puedes reformularlo?")
        ultimo = mensajes[-1]

        if ultimo.rol == "herramienta":
            return self._respuesta_tras_herramienta(mensajes)

        texto = ultimo.contenido
        normalizado = normalizar(texto)
        return (
            self._intentar_sorpresa(texto)
            or self._intentar_calculo(texto)
            or self._intentar_conversion(texto, normalizado)
            or self._intentar_faq(texto, normalizado)
            or self._intentar_reloj(normalizado)
            or self._intentar_stock(texto, normalizado)
            or self._intentar_saludo(normalizado)
            or Respuesta(texto="No estoy seguro, ¿puedes reformularlo?")
        )

    # --- Reglas de decisión -------------------------------------------------
    def _intentar_sorpresa(self, texto: str) -> Respuesta | None:
        respuesta = respuesta_sorpresa(texto)
        return Respuesta(texto=respuesta) if respuesta else None

    def _intentar_calculo(self, texto: str) -> Respuesta | None:
        coincidencia = self._PATRON_OPERACION.search(texto)
        if coincidencia is None:
            return None
        a, operacion, b = coincidencia.groups()
        operacion = "*" if operacion.lower() == "x" else operacion
        return Respuesta(
            herramienta="calculadora",
            argumentos={"a": _a_numero(a), "b": _a_numero(b), "operacion": operacion},
        )

    def _intentar_conversion(self, texto: str, normalizado: str) -> Respuesta | None:
        codigos = [self._CODIGO_MONEDA[m] for m in self._PATRON_MONEDA.findall(normalizado)]
        if not self._MONEDAS_QUE_ACTIVAN.intersection(codigos):
            return None
        numero = self._PATRON_NUMERO.search(texto)
        if numero is None:
            return Respuesta(texto="¿Qué cantidad quieres convertir?")
        origen = codigos[0]
        destino = codigos[1] if len(codigos) > 1 else "EUR"
        return Respuesta(
            herramienta="conversor_moneda",
            argumentos={"cantidad": _a_numero(numero.group()), "origen": origen, "destino": destino},
        )

    def _intentar_faq(self, texto: str, normalizado: str) -> Respuesta | None:
        if self._PATRON_FAQ.search(normalizado) is None:
            return None
        return Respuesta(herramienta="buscador_faq", argumentos={"pregunta": texto})

    def _intentar_reloj(self, normalizado: str) -> Respuesta | None:
        if self._PATRON_RELOJ.search(normalizado) is None:
            return None
        return Respuesta(herramienta="reloj")

    def _intentar_stock(self, texto: str, normalizado: str) -> Respuesta | None:
        if self._PATRON_STOCK.search(normalizado) is None:
            return None
        return Respuesta(herramienta="consulta_stock", argumentos={"producto": texto})

    def _intentar_saludo(self, normalizado: str) -> Respuesta | None:
        if self._PATRON_SALUDO.search(normalizado) is None:
            return None
        return Respuesta(texto="¡Hola! Soy NEXO, ¿en qué te ayudo?")

    # --- Qué hacer tras ejecutarse una herramienta ---------------------------
    def _respuesta_tras_herramienta(self, mensajes: list) -> Respuesta:
        ultimo = mensajes[-1]
        try:
            nombre, resultado, es_error = ultimo.desglosar_herramienta()
        except ValueError:
            return Respuesta(texto=f"Este es el resultado: {ultimo.contenido}")

        if es_error:
            return Respuesta(texto=f"No he podido completar la operación: {resultado}")
        if nombre == "calculadora":
            return Respuesta(texto=self._frase_calculo(mensajes, resultado))
        if nombre == "conversor_moneda":
            return self._encadenar_calculo(mensajes, resultado) or Respuesta(texto=f"{resultado}.")
        if nombre == "buscador_faq":
            if resultado == NO_ENCONTRADO:
                return Respuesta(
                    texto="No he encontrado esa información en nuestras preguntas frecuentes. "
                          "¿Puedes reformularlo?"
                )
            return Respuesta(texto=f"Según nuestra información: {resultado}")
        if nombre == "reloj":
            return Respuesta(texto=resultado)
        if nombre == "consulta_stock":
            if resultado == NO_ENCONTRADO:
                return Respuesta(texto="No he encontrado ese producto en el catálogo. ¿Me dices su nombre?")
            return Respuesta(texto=resultado)
        return Respuesta(texto=f"Este es el resultado: {resultado}")

    def _encadenar_calculo(self, mensajes: list, resultado_conversion: str) -> Respuesta | None:
        """Si el usuario pidió operar con el importe convertido, pide la calculadora."""
        peticion = next((m for m in reversed(mensajes) if m.rol == "usuario"), None)
        importe = self._PATRON_IMPORTE_CONVERTIDO.search(resultado_conversion)
        if peticion is None or importe is None:
            return None
        texto = normalizar(peticion.contenido)
        for patron, operacion in self._CALCULO_ENCADENADO:
            coincidencia = patron.search(texto)
            if coincidencia:
                return Respuesta(
                    herramienta="calculadora",
                    argumentos={
                        "a": _a_numero(importe.group(1)),
                        "b": _a_numero(coincidencia.group(1)),
                        "operacion": operacion,
                    },
                )
        return None

    @staticmethod
    def _frase_calculo(mensajes: list, resultado: str) -> str:
        """Frase para el resultado de la calculadora; menciona la conversión previa si la hubo."""
        if len(mensajes) >= 2 and mensajes[-2].rol == "herramienta":
            try:
                nombre_previo, resultado_previo, _ = mensajes[-2].desglosar_herramienta()
            except ValueError:
                nombre_previo = resultado_previo = ""
            if nombre_previo == "conversor_moneda":
                return f"{resultado_previo}; y luego {resultado}. ¿Necesitas algo más?"
        return f"El resultado es {resultado}. ¿Necesitas algo más?"


class ModeloLLM(Modelo):
    """Modelo compatible con la API de chat completions de OpenAI, con SSE real."""

    remoto = True

    def __init__(
        self,
        nombre: str | None = None,
        api_key: str | None = None,
        api_url: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        coste_por_1000_tokens: float | None = None,
        registrar_uso: Callable[[str, int, float], None] | None = None,
        cliente: httpx.Client | None = None,
        max_tokens_ampliado: int | None = None,
        instruccion: str | None = None,
        esfuerzo_razonamiento: str | None = None,
    ):
        super().__init__(nombre or os.getenv("LLM_MODEL", "gpt-4o"))
        self._api_key = api_key if api_key is not None else os.getenv("LLM_API_KEY", "")
        self._api_url = api_url or os.getenv(
            "LLM_API_URL", "https://api.openai.com/v1/chat/completions"
        )
        self._max_tokens = (
            max_tokens if max_tokens is not None else int(os.getenv("LLM_MAX_TOKENS", "150"))
        )
        self._temperature = (
            temperature if temperature is not None else float(os.getenv("LLM_TEMPERATURE", "0.7"))
        )
        self._coste_por_1000_tokens = (
            coste_por_1000_tokens
            if coste_por_1000_tokens is not None
            else float(os.getenv("LLM_COST_PER_1K_OUTPUT", "0.008"))
        )
        # Tope ampliado: si la respuesta se corta en max_tokens, se continúa hasta este total (0 = sin ampliar).
        self._max_tokens_ampliado = (
            max_tokens_ampliado
            if max_tokens_ampliado is not None
            else int(os.getenv("LLM_MAX_TOKENS_AMPLIADO", "0") or 0)
        )
        self._instruccion = (
            instruccion if instruccion is not None else os.getenv("LLM_SYSTEM", INSTRUCCION_LLM)
        ).strip()
        # Solo para modelos que lo admiten (p. ej. gpt-oss en Groq: low/medium/high). Vacío = no se envía.
        self._esfuerzo = (
            esfuerzo_razonamiento
            if esfuerzo_razonamiento is not None
            else os.getenv("LLM_REASONING_EFFORT", "")
        ).strip()
        self._registrar_uso = registrar_uso
        self._cliente = cliente or httpx.Client(timeout=30)

    def responder(self, conversacion: Conversacion, herramientas: list) -> Respuesta:
        respuesta = None
        for evento in self.responder_por_fragmentos(conversacion, herramientas):
            if evento["tipo"] == "respuesta":
                respuesta = evento["respuesta"]
        if respuesta is None:
            raise ErrorProveedorLLM("El proveedor no devolvió una respuesta.")
        return respuesta

    def responder_por_fragmentos(self, conversacion: Conversacion, herramientas: list) -> Iterator[dict]:
        mensajes = self._mensajes_api(conversacion)
        validar(mensajes, self._max_tokens, self._temperature)
        if not self._api_key:
            raise ErrorProveedorLLM("Configura LLM_API_KEY en el archivo .env del servidor.")

        base = list(mensajes)
        if self._instruccion:
            base.insert(0, {"role": "system", "content": self._instruccion})
        payload = {
            "model": self.nombre,
            "messages": base,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if self._esfuerzo:
            payload["reasoning_effort"] = self._esfuerzo
        esquemas = [herramienta.esquema() for herramienta in herramientas]
        if esquemas:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": esquema["name"],
                        "description": esquema["description"],
                        "parameters": esquema["input_schema"],
                    },
                }
                for esquema in esquemas
            ]
        texto: list[str] = []
        llamadas: dict[int, dict[str, str]] = {}
        tokens_salida, corte = yield from self._leer_stream(payload, texto, llamadas)

        # Respuesta cortada por max_tokens: si hay un tope ampliado, se continúa hasta ese total.
        if corte == "length" and not llamadas and texto:
            restantes = self._max_tokens_ampliado - (tokens_salida or self._max_tokens)
            if restantes > 0:
                continuacion = dict(payload)
                continuacion["max_tokens"] = restantes
                continuacion.pop("tools", None)
                continuacion["messages"] = base + [
                    {"role": "assistant", "content": "".join(texto)},
                    {"role": "user", "content": "Continúa exactamente donde te quedaste, sin repetir nada y sin saludar."},
                ]
                mas_tokens, _ = yield from self._leer_stream(continuacion, texto, llamadas)
                if tokens_salida is not None and mas_tokens is not None:
                    tokens_salida += mas_tokens
                else:
                    tokens_salida = None  # se estimará abajo

        texto_completo = "".join(texto)
        if tokens_salida is None:
            # Algunos proveedores compatibles no envían el uso en streaming: se estima (~4 caracteres/token).
            base_texto = texto_completo or "".join(
                f"{l['name']}{l['arguments']}" for l in llamadas.values()
            )
            tokens_salida = max(1, len(base_texto) // 4)
        if llamadas:
            # Si el modelo pide varias a la vez (pasa con algunos modelos de Groq), se atiende la primera;
            # el bucle del agente podrá pedir la siguiente en la vuelta siguiente.
            llamada = llamadas[min(llamadas)]
            try:
                argumentos = json.loads(llamada["arguments"])
            except json.JSONDecodeError as error:
                raise ErrorProveedorLLM("El proveedor devolvió argumentos de herramienta no válidos.") from error
            if not llamada["name"] or not isinstance(argumentos, dict):
                raise ErrorProveedorLLM("El proveedor devolvió una solicitud de herramienta incompleta.")
            respuesta_modelo = Respuesta(herramienta=llamada["name"], argumentos=argumentos)
        elif texto_completo:
            respuesta_modelo = Respuesta(texto=texto_completo)
        else:
            raise ErrorProveedorLLM("El proveedor devolvió una respuesta vacía.")
        pregunta = next(
            mensaje.contenido
            for mensaje in reversed(conversacion.get_mensajes())
            if mensaje.rol == "usuario"
        )
        coste = tokens_salida * self._coste_por_1000_tokens / 1000
        if self._registrar_uso is not None:
            self._registrar_uso(pregunta, tokens_salida, coste)
        yield {"tipo": "respuesta", "respuesta": respuesta_modelo}

    def _leer_stream(self, payload: dict, texto: list, llamadas: dict):
        """Lee una respuesta en streaming: emite fragmentos y devuelve (tokens_salida, finish_reason)."""
        tokens_salida = None
        corte = None
        try:
            respuesta_http = self._abrir_stream(payload)
        except httpx.HTTPStatusError as error:
            raise ErrorProveedorLLM(
                f"El proveedor rechazó la petición (HTTP {error.response.status_code})."
                f"{_detalle_error_proveedor(error.response)}"
            ) from error
        except httpx.RequestError as error:
            raise ErrorProveedorLLM("No se pudo conectar con el proveedor del modelo.") from error

        try:
            for linea in respuesta_http.iter_lines():
                if not linea.startswith("data:"):
                    continue
                contenido = linea[5:].strip()
                if not contenido or contenido == "[DONE]":
                    continue
                try:
                    fragmento = json.loads(contenido)
                except json.JSONDecodeError as error:
                    raise ErrorProveedorLLM("El proveedor devolvió un fragmento no válido.") from error
                tokens = _tokens_de_uso(fragmento)
                if tokens is not None:
                    tokens_salida = tokens
                elecciones = fragmento.get("choices", [])
                if elecciones:
                    if elecciones[0].get("finish_reason"):
                        corte = elecciones[0]["finish_reason"]
                    delta = elecciones[0].get("delta", {})
                    parte = delta.get("content")
                    if isinstance(parte, str) and parte:
                        texto.append(parte)
                        yield {"tipo": "fragmento", "texto": parte}
                    for llamada in delta.get("tool_calls", []):
                        indice = llamada.get("index", 0)
                        acumulada = llamadas.setdefault(indice, {"name": "", "arguments": ""})
                        funcion = llamada.get("function", {})
                        acumulada["name"] += funcion.get("name", "")
                        acumulada["arguments"] += funcion.get("arguments", "")
        except httpx.RequestError as error:
            raise ErrorProveedorLLM("Se interrumpió la transmisión del proveedor.") from error
        finally:
            respuesta_http.close()
        return tokens_salida, corte

    @retry(
        retry=retry_if_exception(_es_error_reintentable),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _abrir_stream(self, payload: dict) -> httpx.Response:
        solicitud = self._cliente.build_request(
            "POST",
            self._api_url,
            json=payload,
            headers={"Authorization": f"Bearer {self._api_key}"},
        )
        respuesta = self._cliente.send(solicitud, stream=True)
        try:
            respuesta.raise_for_status()
        except httpx.HTTPStatusError:
            try:
                respuesta.read()  # el cuerpo explica el motivo (clave, modelo, límite...)
            except httpx.HTTPError:
                pass
            respuesta.close()
            raise
        return respuesta

    @staticmethod
    def _mensajes_api(conversacion: Conversacion) -> list[dict]:
        mensajes_api = []
        resumen = []
        for mensaje in conversacion.get_mensajes():
            if mensaje.rol == "asistente" and mensaje.contenido.startswith(PREFIJO_RESUMEN):
                resumen.append(mensaje.contenido[len(PREFIJO_RESUMEN):].strip())
                continue
            if mensaje.rol == "usuario":
                contenido = mensaje.contenido
                if resumen:
                    contenido = f"Contexto resumido: {' | '.join(resumen)}\n\n{contenido}"
                    resumen.clear()
                mensajes_api.append({"role": "user", "content": contenido})
            elif mensaje.rol == "asistente":
                mensajes_api.append({"role": "assistant", "content": mensaje.contenido})
            else:
                mensajes_api.append(
                    {"role": "user", "content": f"Resultado de herramienta: {mensaje.contenido}"}
                )
        return mensajes_api

    def cerrar(self) -> None:
        self._cliente.close()
