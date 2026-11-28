import '../estilos/logo.css'

interface Props {
  tamano?: number
  animado?: boolean
  className?: string
  /** Si se indica, el emblema es el único identificador y se anuncia a lectores de pantalla. */
  titulo?: string
}

const MARCAS = Array.from({ length: 24 }, (_, i) => i)

/** Emblema de NEXO: sello corporativo de anillos fragmentados alrededor de un núcleo. */
export function Logo({ tamano = 40, animado = true, className = '', titulo }: Props) {
  return (
    <svg
      className={`logo${animado ? ' logo--animado' : ''} ${className}`.trim()}
      width={tamano}
      height={tamano}
      viewBox="0 0 100 100"
      {...(titulo ? { role: 'img', 'aria-label': titulo } : { 'aria-hidden': true })}
    >
      {titulo && <title>{titulo}</title>}
      <path className="logo__esquina" d="M4 20V4h16M80 4h16v16M96 80v16H80M20 96H4V80" />
      <g className="logo__marcas">
        {MARCAS.map((i) => (
          <line key={i} x1="50" y1={i % 6 === 0 ? 3 : 6} x2="50" y2="9" transform={`rotate(${i * 15} 50 50)`} />
        ))}
      </g>
      <circle className="logo__anillo logo__anillo--exterior" cx="50" cy="50" r="38" />
      <circle className="logo__anillo logo__anillo--medio" cx="50" cy="50" r="28" />
      <circle className="logo__anillo logo__anillo--acento" cx="50" cy="50" r="38" />
      <path className="logo__bisel" d="M50 31l16.5 9.5v19L50 69 33.5 59.5v-19z" />
      <circle className="logo__nucleo" cx="50" cy="50" r="9" />
      <circle className="logo__pupila" cx="50" cy="50" r="3.5" />
    </svg>
  )
}
