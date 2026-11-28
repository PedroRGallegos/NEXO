import { leerSse } from './sse'
import type {
  Conversacion, Estadisticas, EventoHerramienta, Herramienta, Modelo, ResumenConversacion,
} from './tipos'

/** Error de la API con el formato `{"error": {"codigo", "mensaje"}}` del backend. */
export class ErrorApi extends Error {
  constructor(readonly codigo: string, mensaje: string, readonly estado = 0) {
    super(mensaje)
  }
}

async function pedir<T>(ruta: string, opciones?: RequestInit): Promise<T> {
  let respuesta: Response
  try {
    respuesta = await fetch(`/api${ruta}`, {
      ...opciones,
      headers: { 'Content-Type': 'application/json', ...opciones?.headers },
    })
  } catch {
    throw new ErrorApi('sin_conexion', 'No hay conexión con el servidor de NEXO.')
  }
  if (!respuesta.ok) throw await errorDe(respuesta)
  return (await respuesta.json()) as T
}

async function errorDe(respuesta: Response): Promise<ErrorApi> {
  try {
    const { error } = await respuesta.json()
    return new ErrorApi(error.codigo, error.mensaje, respuesta.status)
  } catch {
    return new ErrorApi('error_http', `El servidor respondió con el estado ${respuesta.status}.`, respuesta.status)
  }
}

const post = (cuerpo: unknown): RequestInit => ({ method: 'POST', body: JSON.stringify(cuerpo) })

export type EventoFlujo =
  | { tipo: 'herramienta'; datos: EventoHerramienta }
  | { tipo: 'fragmento'; texto: string }
  | { tipo: 'fin'; conversacion: Conversacion }

export const api = {
  salud: () => pedir<{ estado: string }>('/salud'),
  modelos: () => pedir<Modelo[]>('/modelos'),
  herramientas: () => pedir<Herramienta[]>('/herramientas'),
  estadisticas: () => pedir<Estadisticas>('/estadisticas'),
  listar: () => pedir<ResumenConversacion[]>('/conversaciones'),
  crear: () => pedir<Conversacion>('/conversaciones', { method: 'POST' }),
  obtener: (id: string) => pedir<Conversacion>(`/conversaciones/${encodeURIComponent(id)}`),
  cambiarModelo: (id: string, modelo: string) =>
    pedir<Conversacion>(`/conversaciones/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify({ modelo }) }),

  /** Envía un mensaje y emite los eventos del streaming a medida que llegan. */
  async *enviar(id: string, texto: string): AsyncGenerator<EventoFlujo> {
    let respuesta: Response
    try {
      respuesta = await fetch(`/api/conversaciones/${encodeURIComponent(id)}/mensajes/stream`, {
        ...post({ texto }),
        headers: { 'Content-Type': 'application/json' },
      })
    } catch {
      throw new ErrorApi('sin_conexion', 'No hay conexión con el servidor de NEXO.')
    }
    if (!respuesta.ok || !respuesta.body) throw await errorDe(respuesta)

    for await (const { evento, datos } of leerSse(respuesta.body)) {
      if (evento === 'herramienta') yield { tipo: 'herramienta', datos: datos as EventoHerramienta }
      else if (evento === 'fragmento') yield { tipo: 'fragmento', texto: (datos as { texto: string }).texto }
      else if (evento === 'fin') yield { tipo: 'fin', conversacion: datos as Conversacion }
      else if (evento === 'error') {
        const { codigo, mensaje } = datos as { codigo: string; mensaje: string }
        throw new ErrorApi(codigo, mensaje)
      }
    }
  },
}
