import { describe, expect, it } from 'vitest'
import { leerSse } from './sse'

function flujo(trozos: string[]): ReadableStream<Uint8Array> {
  const codificador = new TextEncoder()
  return new ReadableStream({
    start(control) {
      trozos.forEach((t) => control.enqueue(codificador.encode(t)))
      control.close()
    },
  })
}

async function todos(trozos: string[]) {
  const salida = []
  for await (const e of leerSse(flujo(trozos))) salida.push(e)
  return salida
}

describe('leerSse', () => {
  it('interpreta eventos completos', async () => {
    const eventos = await todos(['event: fragmento\ndata: {"texto": "Hola "}\n\nevent: fin\ndata: {"ok": true}\n\n'])
    expect(eventos).toEqual([
      { evento: 'fragmento', datos: { texto: 'Hola ' } },
      { evento: 'fin', datos: { ok: true } },
    ])
  })

  it('une eventos partidos entre varios trozos, incluso dentro de un carácter UTF-8', async () => {
    const bytes = new TextEncoder().encode('event: fragmento\ndata: {"texto": "ñ"}\n\n')
    const corte = bytes.indexOf(0xc3) + 1 // entre los dos bytes de «ñ»
    const codificado = new ReadableStream<Uint8Array>({
      start(control) {
        control.enqueue(bytes.slice(0, corte))
        control.enqueue(bytes.slice(corte))
        control.close()
      },
    })
    const salida = []
    for await (const e of leerSse(codificado)) salida.push(e)
    expect(salida).toEqual([{ evento: 'fragmento', datos: { texto: 'ñ' } }])
  })

  it('ignora un evento incompleto al final del flujo', async () => {
    expect(await todos(['event: fragmento\ndata: {"texto": "a"}'])).toEqual([])
  })

  it('acepta saltos de línea CRLF', async () => {
    expect(await todos(['event: fin\r\ndata: {"ok": true}\r\n\r\n'])).toEqual([{ evento: 'fin', datos: { ok: true } }])
  })
})
