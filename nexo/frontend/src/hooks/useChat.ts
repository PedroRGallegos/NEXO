import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ErrorApi } from '../api/cliente'
import type { Conversacion, Mensaje, ResumenConversacion } from '../api/tipos'

const INTERVALO_SALUD_MS = 15_000

interface LlamadaHerramienta {
  nombre: string
  argumentos: Record<string, unknown>
}

function mensajeDeHerramienta(nombre: string, resultado: string, error: boolean, argumentos?: Record<string, unknown>): Mensaje {
  return {
    rol: 'herramienta',
    contenido: `[${nombre}] ${error ? 'Error: ' : ''}${resultado}`,
    fecha: new Date().toISOString(),
    argumentos,
  }
}

/** El servidor guarda solo «[nombre] resultado»: se reponen los argumentos de las herramientas del último turno. */
function anotarArgumentos(mensajes: Mensaje[], usadas: LlamadaHerramienta[]): Mensaje[] {
  if (!usadas.length) return mensajes
  const inicio = mensajes.map((m) => m.rol).lastIndexOf('usuario')
  let k = 0
  return mensajes.map((m, i) => {
    const llamada = usadas[k]
    if (i <= inicio || m.rol !== 'herramienta' || !llamada || !m.contenido.startsWith(`[${llamada.nombre}]`)) return m
    k += 1
    return { ...m, argumentos: llamada.argumentos }
  })
}

/** Estado de la aplicación: conversaciones, mensajes (con streaming) y estado del servidor. */
export function useChat() {
  const [conversaciones, setConversaciones] = useState<ResumenConversacion[]>([])
  const [activa, setActiva] = useState<Conversacion | null>(null)
  const [mensajes, setMensajes] = useState<Mensaje[]>([])
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [conectado, setConectado] = useState<boolean | null>(null)
  const [version, setVersion] = useState(0) // sube tras cada respuesta: refresca estadísticas
  const iniciado = useRef(false)
  const activaId = useRef<string | null>(null) // conversación visible ahora mismo

  const [aviso, setAviso] = useState<string | null>(null)

  useEffect(() => {
    if (!aviso) return
    const t = window.setTimeout(() => setAviso(null), 3000)
    return () => window.clearTimeout(t)
  }, [aviso])

  const mostrar = useCallback((conversacion: Conversacion, usadas: LlamadaHerramienta[] = []) => {
    activaId.current = conversacion.id
    setActiva(conversacion)
    setMensajes(anotarArgumentos(conversacion.mensajes, usadas))
  }, [])

  const refrescarLista = useCallback(async () => {
    try {
      setConversaciones(await api.listar())
    } catch {
      /* el estado de conexión ya avisa del problema */
    }
  }, [])

  const informar = (e: unknown) =>
    setError(e instanceof ErrorApi ? e.message : 'Ha ocurrido un error inesperado.')

  const nueva = useCallback(async () => {
    try {
      setError(null)
      mostrar(await api.crear())
    } catch (e) {
      informar(e)
    }
  }, [mostrar])

  /** `/limpiar`: conversación en blanco. La anterior ya está guardada en el servidor y sigue en el historial. */
  const limpiar = useCallback(async () => {
    if (enviando) {
      setAviso('Espera a que NEXO termine de responder')
      return
    }
    if (mensajes.length === 0) {
      setAviso('La conversación ya está vacía')
      return
    }
    await nueva()
    await refrescarLista()
    setAviso('Conversación limpia · la anterior sigue en el historial')
  }, [enviando, mensajes.length, nueva, refrescarLista])

  const abrir = useCallback(
    async (id: string) => {
      try {
        setError(null)
        mostrar(await api.obtener(id))
      } catch (e) {
        informar(e)
      }
    },
    [mostrar],
  )

  const cambiarModelo = useCallback(
    async (modelo: string) => {
      if (!activa) return
      try {
        setError(null)
        mostrar(await api.cambiarModelo(activa.id, modelo))
        setAviso(`Modelo cambiado a ${modelo}`)
      } catch (e) {
        informar(e)
      }
    },
    [activa, mostrar],
  )

  const enviar = useCallback(
    async (texto: string) => {
      if (!activa || enviando) return
      const id = activa.id
      const sigueVisible = () => activaId.current === id
      setError(null)
      setEnviando(true)
      const usadas: LlamadaHerramienta[] = []
      setMensajes((m) => [...m, { rol: 'usuario', contenido: texto, fecha: new Date().toISOString() }])
      try {
        for await (const evento of api.enviar(id, texto)) {
          if (evento.tipo === 'herramienta') {
            const { nombre, argumentos, resultado, error: fallo } = evento.datos
            usadas.push({ nombre, argumentos })
            if (sigueVisible()) setMensajes((m) => [...m, mensajeDeHerramienta(nombre, resultado, fallo, argumentos)])
          } else if (evento.tipo === 'fragmento') {
            if (sigueVisible()) setMensajes((m) => {
              const ultimo = m[m.length - 1]
              if (ultimo?.parcial) return [...m.slice(0, -1), { ...ultimo, contenido: ultimo.contenido + evento.texto }]
              return [...m, { rol: 'asistente', contenido: evento.texto, fecha: new Date().toISOString(), parcial: true }]
            })
          } else if (sigueVisible()) {
            mostrar(evento.conversacion, usadas)
          }
        }
      } catch (e) {
        informar(e)
        try {
          const real = await api.obtener(id)
          if (sigueVisible()) mostrar(real) // descarta lo provisional: manda el estado real del servidor
        } catch {
          /* sin conexión: se deja lo mostrado */
        }
      } finally {
        setEnviando(false)
        setVersion((v) => v + 1)
        void refrescarLista()
      }
    },
    [activa, enviando, mostrar, refrescarLista],
  )

  useEffect(() => {
    if (iniciado.current) return
    iniciado.current = true
    void refrescarLista()
    void nueva()
  }, [nueva, refrescarLista])

  useEffect(() => {
    const comprobar = () =>
      api.salud().then(() => setConectado(true), () => setConectado(false))
    void comprobar()
    const temporizador = setInterval(comprobar, INTERVALO_SALUD_MS)
    return () => clearInterval(temporizador)
  }, [])

  return {
    conversaciones, activa, mensajes, enviando, error, conectado, version,
    aviso, nueva, limpiar, abrir, enviar, cambiarModelo, descartarError: () => setError(null),
  }
}
