import type { Panel } from '../App'
import { Logo } from './Logo'
import type { ResumenConversacion } from '../api/tipos'

interface Props {
  conversaciones: ResumenConversacion[]
  activaId: string | null
  hayConversacionVacia: boolean
  conectado: boolean | null
  panel: Panel
  abierto: boolean
  onNueva: () => void
  onAbrir: (id: string) => void
  onPanel: (panel: Exclude<Panel, null>) => void
  onCerrar: () => void
}

const ESTADO = {
  true: { clase: 'estado--ok', texto: 'Sistema en línea' },
  false: { clase: 'estado--error', texto: 'Sin conexión con la API' },
  null: { clase: 'estado--espera', texto: 'Comprobando…' },
} as const

export function Sidebar({
  conversaciones, activaId, hayConversacionVacia, conectado, panel, abierto, onNueva, onAbrir, onPanel, onCerrar,
}: Props) {
  const estado = ESTADO[String(conectado) as keyof typeof ESTADO]
  const activaEnLista = conversaciones.some((c) => c.id === activaId)

  return (
    <>
      {abierto && <div className="velo" onClick={onCerrar} aria-hidden="true" />}
      <aside className={`sidebar${abierto ? ' sidebar--abierta' : ''}`} aria-label="Navegación">
        <div className="marca">
          <Logo tamano={42} className="marca__emblema" />
          <div>
            <div className="marca__nombre">NEXO</div>
            <div className="marca__sub">TechNova Corp · División IA</div>
          </div>
        </div>

        <button className="boton boton--primario boton--ancho" onClick={onNueva}>
          + Nueva conversación
        </button>
        <p className="sidebar__atajo">o escribe <code>/limpiar</code> en el chat</p>

        <nav className="historial" aria-label="Historial">
          <h2 className="etiqueta">Historial</h2>
          <ul>
            {hayConversacionVacia && !activaEnLista && activaId && (
              <li><span className="historial__item historial__item--activo">Nueva conversación</span></li>
            )}
            {conversaciones.map((c) => (
              <li key={c.id}>
                <button
                  className={`historial__item${c.id === activaId ? ' historial__item--activo' : ''}`}
                  onClick={() => onAbrir(c.id)}
                  aria-current={c.id === activaId ? 'true' : undefined}
                  title={c.titulo}
                >
                  <span className="historial__titulo">{c.titulo}</span>
                  <span className="historial__meta">{c.mensajes} msj</span>
                </button>
              </li>
            ))}
          </ul>
          {conversaciones.length === 0 && !hayConversacionVacia && <p className="vacio">Aún no hay conversaciones.</p>}
          {conversaciones.length === 0 && hayConversacionVacia && <p className="vacio">Tus conversaciones aparecerán aquí.</p>}
        </nav>

        <div className="sidebar__pie">
          <div className="sidebar__atajos">
          <button className={`boton boton--nav${panel === 'config' ? ' boton--activo' : ''}`} onClick={() => onPanel('config')} aria-pressed={panel === 'config'}>
            ⚙ Configuración
          </button>
          <button className={`boton boton--nav${panel === 'stats' ? ' boton--activo' : ''}`} onClick={() => onPanel('stats')} aria-pressed={panel === 'stats'}>
            ▤ Estadísticas
          </button>
          </div>
          <div className={`estado ${estado.clase}`} role="status">
            <span className="estado__led" aria-hidden="true" />
            {estado.texto}
          </div>
        </div>
      </aside>
    </>
  )
}
