/** Convierte el texto Markdown que suelen devolver los modelos (**negrita**, * listas, # títulos…) en una
 *  estructura sencilla. No genera HTML: la interfaz la pinta con elementos de React (sin riesgo de XSS) y
 *  así nunca se ven asteriscos sueltos. Tolera texto a medias, porque la respuesta llega en streaming. */

export type Inline =
  | { tipo: 'texto'; texto: string }
  | { tipo: 'negrita'; texto: string }
  | { tipo: 'cursiva'; texto: string }
  | { tipo: 'codigo'; texto: string }

export type Bloque =
  | { tipo: 'parrafo'; lineas: Inline[][] }
  | { tipo: 'titulo'; contenido: Inline[] }
  | { tipo: 'lista'; ordenada: boolean; items: Inline[][] }

const PATRON_INLINE = /(\*\*[^*\n]+?\*\*|__[^_\n]+?__|`[^`\n]+?`|\*[^*\s][^*\n]*?\*|(?<![\w])_[^_\s][^_\n]*?_(?![\w]))/g

export function inline(texto: string): Inline[] {
  const partes: Inline[] = []
  let ultimo = 0
  for (const m of texto.matchAll(PATRON_INLINE)) {
    const idx = m.index ?? 0
    if (idx > ultimo) partes.push({ tipo: 'texto', texto: limpiar(texto.slice(ultimo, idx)) })
    const t = m[0]
    if (t.startsWith('**') || t.startsWith('__')) partes.push({ tipo: 'negrita', texto: t.slice(2, -2) })
    else if (t.startsWith('`')) partes.push({ tipo: 'codigo', texto: t.slice(1, -1) })
    else partes.push({ tipo: 'cursiva', texto: t.slice(1, -1) })
    ultimo = idx + t.length
  }
  if (ultimo < texto.length) partes.push({ tipo: 'texto', texto: limpiar(texto.slice(ultimo)) })
  return partes.filter((p) => p.texto !== '')
}

/** Quita los marcadores que quedaron sin pareja (p. ej. «**» a medias mientras llega el streaming). */
function limpiar(texto: string): string {
  // Solo se quitan asteriscos que son marcas (pegados a una palabra o repetidos): «3 * 79,9» se conserva.
  return texto
    .replace(/\*{2,}/g, '')
    .replace(/(^|\s)\*(?=\p{L})/gu, '$1')
    .replace(/(?<=\p{L})\*(?=\s|$|[.,;:!?)])/gu, '')
}

const LISTA = /^\s*(?:[*\-•+])\s+(.*)$/
const LISTA_NUM = /^\s*\d+[.)]\s+(.*)$/
const TITULO = /^\s{0,3}#{1,6}\s+(.*)$/
const REGLA = /^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/

export function formatear(texto: string): Bloque[] {
  const bloques: Bloque[] = []
  let parrafo: Inline[][] = []
  let lista: { ordenada: boolean; items: Inline[][] } | null = null
  const cerrarParrafo = () => {
    if (parrafo.length) bloques.push({ tipo: 'parrafo', lineas: parrafo })
    parrafo = []
  }
  const cerrarLista = () => {
    if (lista) bloques.push({ tipo: 'lista', ...lista })
    lista = null
  }
  for (const linea of texto.replace(/\r/g, '').split('\n')) {
    if (!linea.trim() || REGLA.test(linea)) {
      cerrarParrafo()
      cerrarLista()
      continue
    }
    const titulo = TITULO.exec(linea)
    if (titulo) {
      cerrarParrafo()
      cerrarLista()
      bloques.push({ tipo: 'titulo', contenido: inline(titulo[1]) })
      continue
    }
    const punto = LISTA.exec(linea)
    const numero = punto ? null : LISTA_NUM.exec(linea)
    const item = punto ?? numero
    if (item) {
      cerrarParrafo()
      const ordenada = Boolean(numero)
      if (lista && lista.ordenada !== ordenada) cerrarLista()
      lista ??= { ordenada, items: [] }
      lista.items.push(inline(item[1]))
      continue
    }
    cerrarLista()
    parrafo.push(inline(linea.trim()))
  }
  cerrarParrafo()
  cerrarLista()
  return bloques
}

/** Texto plano sin marcas Markdown (para copiar al portapapeles). */
export function aTextoPlano(texto: string): string {
  return formatear(texto)
    .map((b) => {
      const plano = (partes: Inline[]) => partes.map((p) => p.texto).join('')
      if (b.tipo === 'parrafo') return b.lineas.map(plano).join('\n')
      if (b.tipo === 'titulo') return plano(b.contenido)
      return b.items.map((it, i) => `${b.ordenada ? `${i + 1}.` : '•'} ${plano(it)}`).join('\n')
    })
    .join('\n\n')
}
