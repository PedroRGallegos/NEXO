import { describe, expect, it } from 'vitest'
import { esComandoLimpiar } from './comandos'

describe('esComandoLimpiar', () => {
  it('reconoce /limpiar y /clear sin importar mayúsculas ni espacios', () => {
    for (const t of ['/limpiar', '/LIMPIAR', '  /clear  ', '/Clear']) expect(esComandoLimpiar(t)).toBe(true)
  })
  it('no confunde frases normales ni comandos con argumentos', () => {
    for (const t of ['limpiar', 'limpiar la conversación', '/limpiar todo', '/nueva', '', '67']) expect(esComandoLimpiar(t)).toBe(false)
  })
})
