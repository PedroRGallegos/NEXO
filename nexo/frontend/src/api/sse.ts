export interface EventoSse {
  evento: string
  datos: unknown
}

/** Lee un cuerpo `text/event-stream` y emite cada evento en cuanto está completo. */
export async function* leerSse(cuerpo: ReadableStream<Uint8Array>): AsyncGenerator<EventoSse> {
  const lector = cuerpo.getReader()
  const decodificador = new TextDecoder()
  let pendiente = ''
  try {
    for (;;) {
      const { done, value } = await lector.read()
      pendiente += decodificador.decode(value, { stream: !done }).replace(/\r\n?/g, '\n')
      let corte: number
      while ((corte = pendiente.indexOf('\n\n')) >= 0) {
        const evento = interpretar(pendiente.slice(0, corte))
        pendiente = pendiente.slice(corte + 2)
        if (evento) yield evento
      }
      if (done) break
    }
  } finally {
    lector.releaseLock()
  }
}

function interpretar(bloque: string): EventoSse | null {
  let evento = 'message'
  const datos: string[] = []
  for (const linea of bloque.split('\n')) {
    if (linea.startsWith('event:')) evento = linea.slice(6).trim()
    else if (linea.startsWith('data:')) datos.push(linea.slice(5).trimStart())
  }
  if (datos.length === 0) return null
  return { evento, datos: JSON.parse(datos.join('\n')) }
}
