// Contratos de la API (ver presentacion/api.py). Los nombres de campo coinciden con el backend.

export type Rol = 'usuario' | 'asistente' | 'herramienta'

export interface Mensaje {
  rol: Rol
  contenido: string
  fecha: string
  /** Solo en cliente: el texto del asistente aún se está recibiendo. */
  parcial?: boolean
  /** Solo en cliente: argumentos con los que se llamó a la herramienta (mensajes de rol herramienta). */
  argumentos?: Record<string, unknown>
}

export interface Conversacion {
  id: string
  modelo: string
  mensajes: Mensaje[]
  tokens_estimados: number
  limite_tokens: number
}

export interface ResumenConversacion {
  id: string
  titulo: string
  mensajes: number
  actualizada: string
}

export interface Modelo {
  id: string
  nombre: string
  /** 'local' | 'remoto'. Un servidor antiguo puede no enviarlo. */
  tipo?: string
  /** false si el modelo no se puede usar (p. ej. falta la clave del proveedor). */
  disponible?: boolean
  /** Motivo por el que no está disponible. */
  motivo?: string | null
  /** Detalle informativo (p. ej. nombre del modelo del proveedor). */
  detalle?: string | null
}

export interface Herramienta {
  nombre: string
  descripcion: string
  parametros: Record<string, { type?: string; description?: string }>
}

export interface Estadisticas {
  conversaciones: number
  peticiones: number
  tokens_entrada_estimados: number
  tokens_salida_estimados: number
  tokens_salida_llm: number
  coste_eur: number
  nota: string
  herramientas: Record<string, { usos: number; fallos: number }>
}

export interface EventoHerramienta {
  tipo: 'herramienta'
  nombre: string
  argumentos: Record<string, unknown>
  resultado: string
  error: boolean
}
