import { useEffect, useState } from 'react'
import type { Mensaje as MensajeTipo } from '../api/tipos'
import { separarImagen } from '../imagenes'
import { aTextoPlano } from '../formato'
import { TextoFormateado } from './TextoFormateado'

const PATRON_HERRAMIENTA = /^\[([^\]]+)\]\s*(Error: )?([\s\S]*)$/

async function copiar(texto: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(texto)
    return true
  } catch {
    return false
  }
}

function formatearArgumentos(argumentos: Record<string, unknown>): string {
  return Object.entries(argumentos)
    .map(([clave, valor]) => `${clave}=${typeof valor === 'string' ? `'${valor}'` : String(valor)}`)
    .join(', ')
}

function Herramienta({ contenido, argumentos }: { contenido: string; argumentos?: Record<string, unknown> }) {
  const partes = PATRON_HERRAMIENTA.exec(contenido)
  const [, nombre = 'herramienta', error, resultado = contenido] = partes ?? []
  return (
    <div className={`herramienta${error ? ' herramienta--error' : ''}`}>
      <span className="herramienta__nombre">⚙ {nombre}</span>
      {argumentos && <span className="herramienta__args">({formatearArgumentos(argumentos)})</span>}
      <span className="herramienta__resultado">{error ? `Error: ${resultado}` : resultado}</span>
    </div>
  )
}

export function Mensaje({ mensaje }: { mensaje: MensajeTipo }) {
  const [copiado, setCopiado] = useState(false)

  const esUsuario = mensaje.rol === 'usuario'
  const { texto, imagen } = separarImagen(mensaje.contenido)
  useEffect(() => {
    if (!copiado) return
    const t = setTimeout(() => setCopiado(false), 1500)
    return () => clearTimeout(t)
  }, [copiado])
  if (mensaje.rol === 'herramienta') return <Herramienta contenido={mensaje.contenido} argumentos={mensaje.argumentos} />
  const alCopiar = async () => {
    if (await copiar(esUsuario ? texto || mensaje.contenido : aTextoPlano(texto || mensaje.contenido))) setCopiado(true)
  }

  return (
    <article className={`mensaje ${esUsuario ? 'mensaje--usuario' : 'mensaje--nexo'}`}>
      <header className="mensaje__autor">{esUsuario ? 'operador' : 'NEXO'}</header>
      {/* React escapa el texto: no se interpreta HTML (sin riesgo de XSS) */}
      {(texto || !imagen) && (
        <div className="mensaje__texto">
          {esUsuario ? texto : <TextoFormateado texto={texto} />}
          {mensaje.parcial && <span className="cursor" aria-hidden="true" />}
        </div>
      )}
      {imagen && (
        <img className="mensaje__imagen" src={imagen.ruta} alt={imagen.descripcion} width={900} height={576} loading="eager" />
      )}
      {!esUsuario && !mensaje.parcial && (
        <button className="mensaje__copiar" onClick={alCopiar} aria-label="Copiar respuesta">
          {copiado ? '✔ copiado' : 'copiar'}
        </button>
      )}
    </article>
  )
}
