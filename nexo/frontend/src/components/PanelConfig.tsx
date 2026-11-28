import { useEffect, useState } from 'react'
import { api } from '../api/cliente'
import type { Herramienta, Modelo } from '../api/tipos'
import { agruparModelos, estaDisponible } from '../modelos'

const DESCRIPCION_MODELO: Record<string, string> = {
  reglas: 'Decide con reglas: detecta la intención y pide la herramienta adecuada.',
  eco: 'Repite tu último mensaje. Sirve para comprobar que todo está conectado.',
  llm: 'Genera respuestas en streaming con el modelo configurado en el servidor.',
}

interface Props {
  modeloActual: string | null
  onModelo: (modelo: string) => void
  onCerrar: () => void
}

export function PanelConfig({ modeloActual, onModelo, onCerrar }: Props) {
  const [modelos, setModelos] = useState<Modelo[]>([])
  const [herramientas, setHerramientas] = useState<Herramienta[]>([])
  const [fallo, setFallo] = useState(false)

  useEffect(() => {
    Promise.all([api.modelos(), api.herramientas()]).then(
      ([m, h]) => {
        setModelos(m)
        setHerramientas(h)
      },
      () => setFallo(true),
    )
  }, [])

  const { locales, remotos } = agruparModelos(modelos)

  const renderOpcion = (m: Modelo) => {
    const disponible = estaDisponible(m)
    const activa = m.id === modeloActual
    return (
      <button
        key={m.id}
        role="radio"
        aria-checked={activa}
        aria-disabled={!disponible || undefined}
        disabled={!disponible}
        className={`opcion${activa ? ' opcion--activa' : ''}${disponible ? '' : ' opcion--desactivada'}`}
        onClick={() => disponible && !activa && onModelo(m.id)}
      >
        <strong>
          {m.nombre}
          {!disponible && <em className="opcion__etiqueta">NO CONFIGURADO</em>}
        </strong>
        <span>{DESCRIPCION_MODELO[m.id] ?? ''}</span>
        {!disponible && m.motivo && <span className="opcion__motivo">{m.motivo}</span>}
        {disponible && m.detalle && <span className="opcion__detalle">Modelo: {m.detalle}</span>}
      </button>
    )
  }

  return (
    <aside className="panel" aria-label="Configuración">
      <header className="panel__cabecera">
        <h2>Configuración</h2>
        <button className="boton boton--icono" onClick={onCerrar} aria-label="Cerrar panel">✕</button>
      </header>

      {fallo && <p className="vacio">No se pudo cargar la configuración.</p>}

      <h3 className="etiqueta">Modelo de la conversación</h3>
      {locales.length > 0 && (
        <>
          <p className="grupo-rotulo" id="grupo-locales">Modelos locales</p>
          <div className="opciones" role="radiogroup" aria-labelledby="grupo-locales">
            {locales.map(renderOpcion)}
          </div>
        </>
      )}
      {remotos.length > 0 && (
        <>
          <hr className="separador-modelos" />
          <p className="grupo-rotulo" id="grupo-remotos">Modelo remoto · API</p>
          <div className="opciones" role="radiogroup" aria-labelledby="grupo-remotos">
            {remotos.map(renderOpcion)}
          </div>
        </>
      )}
      <p className="nota">La clave del proveedor solo se guarda en el servidor (archivo <code>.env</code>).</p>

      <h3 className="etiqueta">Herramientas disponibles</h3>
      <ul className="lista-herramientas">
        {herramientas.map((h) => (
          <li key={h.nombre}>
            <strong>{h.nombre}</strong>
            <span>{h.descripcion}</span>
          </li>
        ))}
      </ul>
    </aside>
  )
}
