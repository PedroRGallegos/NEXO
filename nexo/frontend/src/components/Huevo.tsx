import { useEffect } from 'react'
import type { Huevo as TipoHuevo } from '../huevos'

const DURACION_MS = 4200

/** Piloto original (SVG propio, sin personajes ni personas reales). */
function Piloto() {
  const confeti = Array.from({ length: 14 }, (_, i) => i)
  return (
    <svg className="huevo__svg" viewBox="0 0 240 260" role="img" aria-label="Piloto de carreras celebrando una victoria">
      {confeti.map((i) => (
        <rect key={i} x={20 + i * 15} y="-10" width="6" height="10" className={`huevo__confeti huevo__confeti--${i % 4}`} style={{ animationDelay: `${(i % 7) * -0.3}s` }} />
      ))}
      <g className="huevo__piloto">
        <rect x="88" y="120" width="64" height="86" rx="14" className="huevo__mono" />
        <rect x="96" y="206" width="20" height="40" rx="6" className="huevo__mono" />
        <rect x="124" y="206" width="20" height="40" rx="6" className="huevo__mono" />
        <path d="M92 130 L56 70" className="huevo__brazo-piloto" />
        <path d="M148 130 L184 70" className="huevo__brazo-piloto" />
        <circle cx="54" cy="66" r="10" className="huevo__guante" />
        <circle cx="186" cy="66" r="10" className="huevo__guante" />
        <circle cx="120" cy="82" r="38" className="huevo__casco" />
        <path d="M92 80h56v20a10 10 0 0 1-10 10h-36a10 10 0 0 1-10-10z" className="huevo__visor" />
        <path d="M104 60q16-14 32 0" className="huevo__brillo" />
      </g>
      <g className="huevo__copa">
        <path d="M104 6h32v22a16 16 0 0 1-32 0z" className="huevo__oro" />
        <rect x="114" y="42" width="12" height="8" className="huevo__oro" />
        <rect x="106" y="50" width="28" height="6" rx="2" className="huevo__oro" />
      </g>
    </svg>
  )
}

interface Props {
  tipo: TipoHuevo
  onTerminar: () => void
}

export function Huevo({ tipo, onTerminar }: Props) {
  useEffect(() => {
    const t = window.setTimeout(onTerminar, DURACION_MS)
    return () => window.clearTimeout(t)
  }, [tipo, onTerminar])

  return (
    <div className="huevo" role="dialog" aria-label="Sorpresa" onClick={onTerminar}>
      <div className="huevo__caja">
        <Piloto />
        <p className="huevo__texto">¡VICTORIA!</p>
        {tipo === 'victoria' && <p className="huevo__sub">Fernando Alonso</p>}
        <button className="boton boton--icono huevo__cerrar" onClick={onTerminar} aria-label="Cerrar sorpresa">✕</button>
      </div>
    </div>
  )
}
