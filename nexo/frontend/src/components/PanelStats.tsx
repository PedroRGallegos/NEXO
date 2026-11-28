import { useEffect, useState } from 'react'
import { api } from '../api/cliente'
import type { Estadisticas } from '../api/tipos'

const numero = new Intl.NumberFormat('es-ES')
const euros = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' })

interface Props {
  version: number
  onCerrar: () => void
}

export function PanelStats({ version, onCerrar }: Props) {
  const [datos, setDatos] = useState<Estadisticas | null>(null)
  const [fallo, setFallo] = useState(false)

  useEffect(() => {
    api.estadisticas().then(
      (d) => {
        setDatos(d)
        setFallo(false)
      },
      () => setFallo(true),
    )
  }, [version])

  const herramientas = Object.entries(datos?.herramientas ?? {})
  const maximo = Math.max(1, ...herramientas.map(([, h]) => h.usos))

  return (
    <aside className="panel" aria-label="Estadísticas">
      <header className="panel__cabecera">
        <h2>Estadísticas</h2>
        <button className="boton boton--icono" onClick={onCerrar} aria-label="Cerrar panel">✕</button>
      </header>

      {fallo && <p className="vacio">No se pudieron cargar las estadísticas.</p>}
      {datos && (
        <>
          <div className="tarjetas">
            <Tarjeta etiqueta="Peticiones" valor={numero.format(datos.peticiones)} />
            <Tarjeta etiqueta="Conversaciones" valor={numero.format(datos.conversaciones)} />
            <Tarjeta etiqueta="Tokens entrada*" valor={numero.format(datos.tokens_entrada_estimados)} />
            <Tarjeta etiqueta="Tokens salida*" valor={numero.format(datos.tokens_salida_estimados)} />
            <Tarjeta etiqueta="Tokens LLM reales" valor={numero.format(datos.tokens_salida_llm)} />
            <Tarjeta etiqueta="Coste" valor={euros.format(datos.coste_eur)} />
          </div>
          <p className="nota">* {datos.nota}</p>

          <h3 className="etiqueta">Uso de herramientas</h3>
          {herramientas.length === 0 && <p className="vacio">Todavía no se ha usado ninguna herramienta.</p>}
          <ul className="barras">
            {herramientas.map(([nombre, h]) => (
              <li key={nombre}>
                <div className="barras__fila"><strong>{nombre}</strong><span>{h.usos} usos · {h.fallos} fallos</span></div>
                <div className="barras__pista"><div className="barras__valor" style={{ width: `${(h.usos / maximo) * 100}%` }} /></div>
              </li>
            ))}
          </ul>
        </>
      )}
    </aside>
  )
}

function Tarjeta({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  return (
    <div className="tarjeta">
      <span className="tarjeta__valor">{valor}</span>
      <span className="tarjeta__etiqueta">{etiqueta}</span>
    </div>
  )
}
