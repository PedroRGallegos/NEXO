import { useRef, useState, type FormEvent, type KeyboardEvent } from 'react'

export const MAX_CARACTERES = 2000

interface Props {
  deshabilitado: boolean
  enviando: boolean
  onEnviar: (texto: string) => void
}

export function Composer({ deshabilitado, enviando, onEnviar }: Props) {
  const [texto, setTexto] = useState('')
  const campo = useRef<HTMLTextAreaElement>(null)
  const limpio = texto.trim()
  const puedeEnviar = limpio.length > 0 && !deshabilitado && !enviando

  const enviar = (e?: FormEvent) => {
    e?.preventDefault()
    if (!puedeEnviar) return
    onEnviar(limpio)
    setTexto('')
    campo.current?.focus()
  }

  const alPulsar = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      enviar()
    }
  }

  return (
    <form className="composer" onSubmit={enviar}>
      <label htmlFor="mensaje" className="solo-lector">Mensaje para NEXO</label>
      <div className="composer__campo">
      <textarea
        id="mensaje"
        ref={campo}
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        onKeyDown={alPulsar}
        placeholder="Introduce un comando para NEXO…"
        title="Enter envía · Mayús+Enter inserta un salto de línea · /limpiar empieza una conversación en blanco"
        rows={1}
        maxLength={MAX_CARACTERES}
        disabled={deshabilitado}
      />
      <span className="composer__contador" aria-hidden="true">{texto.length}/{MAX_CARACTERES}</span>
      </div>
      <button className="boton boton--primario" type="submit" disabled={!puedeEnviar}>
        {enviando ? 'Enviando…' : 'Enviar'}
      </button>
      <p className="composer__ayuda">Enter envía · Mayús+Enter salto de línea · <code>/limpiar</code> empieza una conversación en blanco</p>
    </form>
  )
}
