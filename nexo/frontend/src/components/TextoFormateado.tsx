import { Fragment } from 'react'
import { formatear, type Inline } from '../formato'

function Linea({ partes }: { partes: Inline[] }) {
  return (
    <>
      {partes.map((p, i) =>
        p.tipo === 'negrita' ? <strong key={i}>{p.texto}</strong>
        : p.tipo === 'cursiva' ? <em key={i}>{p.texto}</em>
        : p.tipo === 'codigo' ? <code key={i}>{p.texto}</code>
        : <Fragment key={i}>{p.texto}</Fragment>,
      )}
    </>
  )
}

/** Respuesta de NEXO con el Markdown ya resuelto: negrita, cursiva, listas y títulos, sin asteriscos. */
export function TextoFormateado({ texto }: { texto: string }) {
  return (
    <div className="formato">
      {formatear(texto).map((b, i) =>
        b.tipo === 'titulo' ? <p key={i} className="formato__titulo"><Linea partes={b.contenido} /></p>
        : b.tipo === 'lista' ? (
          b.ordenada
            ? <ol key={i} className="formato__lista">{b.items.map((it, j) => <li key={j}><Linea partes={it} /></li>)}</ol>
            : <ul key={i} className="formato__lista">{b.items.map((it, j) => <li key={j}><Linea partes={it} /></li>)}</ul>
        ) : (
          <p key={i}>
            {b.lineas.map((l, j) => <Fragment key={j}>{j > 0 && <br />}<Linea partes={l} /></Fragment>)}
          </p>
        ),
      )}
    </div>
  )
}
