import { useEffect, useRef, useState, type PointerEvent } from 'react'
import { GeneradorVoz } from '../voz'
import { EsferaJarvis } from './EsferaJarvis'

interface Props {
  conversacionId: string | null
  hablando: boolean
  procesando: boolean
  comando: string
  respuesta: string
  modelo: string | null
  tokens: number
  limite: number
  conectado: boolean | null
}

const DURACION_VISUALIZACION_MS = 1400
export function NexoFace({ conversacionId, hablando, procesando, comando, respuesta, modelo, tokens, limite, conectado }: Props) {
  const [colaHablando, setColaHablando] = useState(false)
  const [voz] = useState(() => new GeneradorVoz())
  const marco = useRef<HTMLDivElement>(null)
  const nucleo = useRef<HTMLDivElement>(null)
  const inclinacion = useRef({ x: 0, y: 0 })
  const frameMovimiento = useRef<number | null>(null)
  const conversacionAnterior = useRef(conversacionId)
  const respuestaAnterior = useRef(respuesta)
  const activa = hablando || colaHablando
  const pensando = procesando && !activa

  useEffect(() => {
    if (conversacionAnterior.current !== conversacionId) {
      conversacionAnterior.current = conversacionId
      respuestaAnterior.current = respuesta
      voz.reiniciar()
      setColaHablando(false)
      return
    }

    if (!respuesta) {
      respuestaAnterior.current = ''
      voz.reiniciar()
      setColaHablando(false)
      return
    }

    const previa = respuestaAnterior.current
    if (respuesta === previa) return
    respuestaAnterior.current = respuesta
    // Solo se «dice» lo que llega nuevo; si el servidor reenvía el mismo texto (p. ej. sin espacios finales) no se repite.
    const nuevo = respuesta.startsWith(previa) ? respuesta.slice(previa.length) : respuesta.trim() === previa.trim() ? '' : respuesta
    voz.empujar(nuevo)
    setColaHablando(true)
    // La esfera sigue «hablando» el tiempo que tarda en decir lo que hay en cola.
    const ms = Math.max(DURACION_VISUALIZACION_MS, voz.segundosPendientes() * 1000 + 300)
    const temporizador = window.setTimeout(() => setColaHablando(false), ms)
    return () => window.clearTimeout(temporizador)
  }, [conversacionId, respuesta, voz])

  useEffect(() => () => {
    if (frameMovimiento.current !== null) window.cancelAnimationFrame(frameMovimiento.current)
  }, [])

  const actualizarInclinacion = () => {
    if (frameMovimiento.current !== null) return
    frameMovimiento.current = window.requestAnimationFrame(() => {
      nucleo.current?.style.setProperty('--nexo-inclinacion-x', `${inclinacion.current.x}deg`)
      nucleo.current?.style.setProperty('--nexo-inclinacion-y', `${inclinacion.current.y}deg`)
      frameMovimiento.current = null
    })
  }

  const seguirCursor = (evento: PointerEvent<HTMLElement>) => {
    const limites = marco.current?.getBoundingClientRect()
    if (!limites) return
    const x = Math.max(-0.5, Math.min(0.5, (evento.clientX - limites.left) / limites.width - 0.5))
    const y = Math.max(-0.5, Math.min(0.5, (evento.clientY - limites.top) / limites.height - 0.5))
    inclinacion.current = { x: -y * 7, y: x * 9 }
    actualizarInclinacion()
  }

  const centrar = () => {
    inclinacion.current = { x: 0, y: 0 }
    actualizarInclinacion()
  }
  const estado = activa ? 'hablando' : pensando ? 'pensando' : 'en espera'

  const porcentaje = Math.min(100, Math.round((tokens / Math.max(1, limite)) * 100))
  const enlace = conectado === null ? 'COMPROBANDO' : conectado ? 'API EN LÍNEA' : 'SIN CONEXIÓN'

  return (
    <section
      className={`nexo-visual${activa ? ' nexo-visual--hablando' : ''}${pensando ? ' nexo-visual--pensando' : ''}`}
      aria-label={`Núcleo visual de NEXO, ${estado}`}
      onPointerMove={seguirCursor}
      onPointerLeave={centrar}
    >
      <div className="nexo-visual__marco" aria-hidden="true"><i /><i /><i /><i /></div>

      <div className="nexo-visual__cabecera">
        <span className="nexo-visual__identidad"><i /> NEXO <b>/</b> NÚCLEO COGNITIVO</span>
        <span className="nexo-visual__canal"><i /> {enlace}</span>
      </div>

      <div className="nexo-visual__hud nexo-visual__hud--izquierdo" aria-label="Datos de la conversación">
        <span className="nexo-visual__etiqueta">MODELO</span>
        <strong className="nexo-visual__valor">{modelo ?? '—'}</strong>
        <span className="nexo-visual__etiqueta">CONTEXTO (ESTIMADO)</span>
        <span className="nexo-visual__dato">{tokens}<small> / {limite} tokens</small></span>
        <span className="nexo-visual__barra"><i style={{ width: `${porcentaje}%` }} /></span>
      </div>

      <div className="nexo-visual__centro" ref={marco}>
        <div className="nexo-visual__nucleo" ref={nucleo}>
          <EsferaJarvis estado={activa ? 'hablando' : pensando ? 'pensando' : 'espera'} voz={voz} />
        </div>
      </div>

      <div className="nexo-visual__hud nexo-visual__hud--derecho">
        <span className="nexo-visual__etiqueta">ESTADO</span>
        <strong className="nexo-visual__estado" role="status" aria-live="polite">
          {activa ? 'RESPONDIENDO' : pensando ? 'PROCESANDO' : 'EN ESPERA'}
        </strong>
        <span className="nexo-visual__etiqueta nexo-visual__etiqueta--comando">ÚLTIMO COMANDO</span>
        <span className="nexo-visual__comando" title={comando || 'Sin comandos'}>
          {comando || 'SIN COMANDOS'}
        </span>
      </div>
    </section>
  )
}
