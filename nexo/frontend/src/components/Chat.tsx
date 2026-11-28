import { useEffect, useRef } from 'react'
import type { Conversacion, Mensaje as MensajeTipo } from '../api/tipos'
import { Composer } from './Composer'
import { Logo } from './Logo'
import { Mensaje } from './Mensaje'
import { NexoFace } from './NexoFace'

const EJEMPLOS = [
  'convierte 100 USD a euros y multiplícalo por 3',
  'cuánto tarda el envío?',
  'cuántas unidades de teclado mecánico quedan?',
  'qué hora es?',
]

interface Props {
  conversacion: Conversacion | null
  mensajes: MensajeTipo[]
  enviando: boolean
  error: string | null
  onEnviar: (texto: string) => void
  onDescartarError: () => void
  onMenu: () => void
  conectado: boolean | null
  aviso: string | null
}

export function Chat({ conversacion, mensajes, enviando, error, onEnviar, onDescartarError, onMenu, conectado, aviso }: Props) {
  const final = useRef<HTMLDivElement>(null)
  const ultimo = mensajes[mensajes.length - 1]
  const generando = enviando && !(ultimo?.rol === 'asistente')
  const ultimoComando = [...mensajes].reverse().find((mensaje) => mensaje.rol === 'usuario')?.contenido ?? ''

  useEffect(() => {
    final.current?.scrollIntoView({ block: 'end' })
  }, [mensajes.length, ultimo?.contenido])

  const tokens = conversacion?.tokens_estimados ?? 0
  const limite = conversacion?.limite_tokens ?? 1
  const porcentaje = Math.min(100, Math.round((tokens / limite) * 100))

  return (
    <main className="chat">
      <header className="cabecera">
        <button className="boton boton--icono menu" onClick={onMenu} aria-label="Abrir menú">☰</button>
        <div className="cabecera__titulo">
          <span className="chip">modelo · {conversacion?.modelo ?? '—'}</span>
          {conversacion && (
            <span className="chip chip--sesion" title="Las conversaciones se guardan solas en disco tras cada respuesta">
              sesión {conversacion.id.slice(0, 8)} · {mensajes.length > 0 ? 'guardada' : 'nueva'}
            </span>
          )}
        </div>
        <div className="medidor" title="Tokens estimados de la conversación (palabras × 1,3)">
          <span className="medidor__texto">contexto {tokens}/{limite}</span>
          <span className="medidor__barra"><span className={`medidor__relleno${porcentaje >= 80 ? ' medidor__relleno--alto' : ''}`} style={{ width: `${porcentaje}%` }} /></span>
        </div>
      </header>

      {aviso && <p className="aviso" role="status">✔ {aviso}</p>}

      <NexoFace
        conversacionId={conversacion?.id ?? null}
        hablando={enviando && ultimo?.rol === 'asistente'}
        procesando={generando}
        comando={ultimoComando}
        respuesta={ultimo?.rol === 'asistente' ? ultimo.contenido : ''}
        modelo={conversacion?.modelo ?? null}
        tokens={tokens}
        limite={limite}
        conectado={conectado}
      />

      <section
        className="mensajes"
        aria-live="polite"
        aria-label="Conversación"
        onLoadCapture={() => final.current?.scrollIntoView({ block: 'end' })} // al cargar una imagen el contenido crece: se vuelve al final
      >
        {mensajes.length === 0 ? (
          <div className="bienvenida">
            <Logo tamano={72} />
            <h1>NEXO en línea</h1>
            <p>Calculadora, conversor de moneda, preguntas frecuentes, stock y hora. Pregunta lo que necesites o prueba un ejemplo:</p>
            <ul className="arranque" aria-label="Estado de arranque">
              <li>Núcleo cognitivo · en línea</li>
              <li>Módulos de herramientas · cargados</li>
              <li>Canal local · activo</li>
            </ul>
            <div className="ejemplos">
              {EJEMPLOS.map((e) => (
                <button key={e} className="ejemplo" onClick={() => onEnviar(e)} disabled={!conversacion || enviando}>{e}</button>
              ))}
            </div>
          </div>
        ) : (
          mensajes.map((m, i) => <Mensaje key={`${i}-${m.rol}`} mensaje={m} />)
        )}
        {generando && (
          <div className="generando" role="status"><span className="puntos" aria-hidden="true"><i /><i /><i /></span>Procesando solicitud…</div>
        )}
        <div ref={final} />
      </section>

      {error && (
        <div className="alerta" role="alert">
          <span>⚠ {error}</span>
          <button className="boton boton--icono" onClick={onDescartarError} aria-label="Cerrar aviso">✕</button>
        </div>
      )}
      <Composer deshabilitado={!conversacion} enviando={enviando} onEnviar={onEnviar} />
    </main>
  )
}
