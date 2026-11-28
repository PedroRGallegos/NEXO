import { describe, expect, it } from 'vitest'
import { aTextoPlano, formatear, inline } from './formato'

describe('formatear', () => {
  it('convierte **negrita** y *cursiva* sin dejar asteriscos', () => {
    expect(inline('Es **muy** útil y *claro*')).toEqual([
      { tipo: 'texto', texto: 'Es ' }, { tipo: 'negrita', texto: 'muy' },
      { tipo: 'texto', texto: ' útil y ' }, { tipo: 'cursiva', texto: 'claro' },
    ])
  })
  it('las listas con * o - pasan a ser listas', () => {
    expect(formatear('Pasos:\n* uno\n* **dos**\n- tres')).toEqual([
      { tipo: 'parrafo', lineas: [[{ tipo: 'texto', texto: 'Pasos:' }]] },
      { tipo: 'lista', ordenada: false, items: [[{ tipo: 'texto', texto: 'uno' }], [{ tipo: 'negrita', texto: 'dos' }], [{ tipo: 'texto', texto: 'tres' }]] },
    ])
  })
  it('listas numeradas y títulos', () => {
    const b = formatear('## Título\n1. a\n2. b')
    expect(b[0]).toEqual({ tipo: 'titulo', contenido: [{ tipo: 'texto', texto: 'Título' }] })
    expect(b[1]).toMatchObject({ tipo: 'lista', ordenada: true })
  })
  it('un marcador a medias (streaming) no deja asteriscos', () => {
    expect(aTextoPlano('Esto es **import')).toBe('Esto es import')
    expect(aTextoPlano('El resultado es 3 * 79.9 = 239.7')).toBe('El resultado es 3 * 79.9 = 239.7')
  })
  it('aTextoPlano devuelve texto limpio', () => {
    expect(aTextoPlano('**Hola**\n\n* a\n* b')).toBe('Hola\n\n• a\n• b')
  })
})
