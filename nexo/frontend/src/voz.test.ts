import { describe, expect, it } from 'vitest'
import { GeneradorVoz, trocear } from './voz'

const silabas = (t: string) => trocear(t).filter((u) => u.tipo === 'silaba').length
const pausas = (t: string) => trocear(t).filter((u) => u.tipo === 'pausa')

describe('trocear', () => {
  it('cuenta una sílaba por grupo de vocales', () => {
    expect(silabas('hola')).toBe(2)
    expect(silabas('resultado')).toBe(4)
    expect(silabas('xyz')).toBe(0)
  })
  it('las comas y los puntos generan pausas, más largas con el punto', () => {
    const [coma] = pausas('sí, vale')
    const [punto] = pausas('sí. vale')
    expect(coma.duracion).toBeLessThan(punto.duracion)
  })
  it('un decimal como 239.7 no se parte con una pausa', () => {
    expect(pausas('239.7')).toHaveLength(0)
    expect(silabas('239.7')).toBe(4)
  })
  it('es determinista', () => {
    expect(trocear('El resultado es 3 * 79.9.')).toEqual(trocear('El resultado es 3 * 79.9.'))
  })
})

describe('GeneradorVoz', () => {
  const correr = (g: GeneradorVoz, segundos: number) => {
    let maximo = 0
    for (let t = 0; t < segundos; t += 1 / 30) maximo = Math.max(maximo, g.avanzar(1 / 30))
    return maximo
  }

  it('en silencio el nivel es 0 y no está activa', () => {
    const g = new GeneradorVoz()
    expect(correr(g, 1)).toBe(0)
    expect(g.activa).toBe(false)
  })

  it('al llegar texto sube el nivel, cuenta sílabas y al terminar vuelve a 0', () => {
    const g = new GeneradorVoz()
    g.empujar('Hola, ¿en qué te ayudo?')
    expect(g.activa).toBe(true)
    expect(correr(g, 1.5)).toBeGreaterThan(0.4)
    expect(g.contador).toBeGreaterThan(3)
    correr(g, 6)
    expect(g.nivel).toBe(0)
    expect(g.activa).toBe(false)
  })

  it('con mucho texto pendiente acelera: no tarda más de unos 4 s', () => {
    const g = new GeneradorVoz()
    g.empujar('El resultado de la operación es correcto y no necesitas nada más. '.repeat(4))
    expect(g.segundosPendientes()).toBeLessThanOrEqual(4.5)
  })

  it('reiniciar corta la voz al instante', () => {
    const g = new GeneradorVoz()
    g.empujar('un texto largo para que haya voz en cola')
    correr(g, 0.5)
    g.reiniciar()
    expect(g.activa).toBe(false)
    expect(g.nivel).toBe(0)
  })

  it('el nivel nunca pasa de 1 ni baja de 0', () => {
    const g = new GeneradorVoz()
    g.empujar('aaaaa eeeee ooooo ¡Increíble! 1234567890')
    for (let i = 0; i < 300; i++) {
      const n = g.avanzar(1 / 30)
      expect(n).toBeGreaterThanOrEqual(0)
      expect(n).toBeLessThanOrEqual(1)
    }
  })
})
