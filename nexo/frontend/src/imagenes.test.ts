import { describe, expect, it } from 'vitest'
import { separarImagen } from './imagenes'

describe('separarImagen', () => {
  it('convierte la marca de Alonso en una imagen con descripción y sin texto', () => {
    const r = separarImagen('[[imagen:/sorpresas/fernando-alonso.jpg]]')
    expect(r.texto).toBe('')
    expect(r.imagen?.ruta).toBe('/sorpresas/fernando-alonso.jpg')
    expect(r.imagen?.descripcion).toBe('Fernando Alonso')
  })
  it('conserva el texto que acompaña a la imagen', () => {
    const r = separarImagen('Mira esto [[imagen:/sorpresas/fernando-alonso.jpg]]')
    expect(r.texto).toBe('Mira esto')
    expect(r.imagen?.ruta).toBe('/sorpresas/fernando-alonso.jpg')
  })
  it('rechaza rutas externas o fuera de /sorpresas/ (sin imagen y sin mostrar la marca)', () => {
    for (const ruta of ['https://x.com/a.jpg', '//x.com/a.jpg', '/otra/a.jpg', '/sorpresas/../a.jpg', 'javascript:alert(1)']) {
      expect(separarImagen(`[[imagen:${ruta}]]`).imagen).toBe(undefined)
    }
  })
  it('no toca los mensajes normales', () => {
    expect(separarImagen('Hola, ¿qué tal?').texto).toBe('Hola, ¿qué tal?')
    expect(separarImagen('El resultado es 3 * 79.9 = 239.7').imagen).toBe(undefined)
  })
  it('oculta una marca a medio llegar por el streaming', () => {
    expect(separarImagen('Hola [[imagen:/sorpresas/fern').texto).toBe('Hola')
  })
})
