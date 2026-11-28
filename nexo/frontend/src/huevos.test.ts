import { describe, expect, it } from 'vitest'
import { detectarHuevo } from './huevos'

describe('detectarHuevo', () => {
  it('el 67 ya no activa ninguna sorpresa', () => {
    for (const t of ['67', ' 67 ', '6 7', 'Six Seven', 'seis siete']) expect(detectarHuevo(t)).toBeNull()
  })
  it('reconoce «Fernando Alonso» con cualquier mezcla de mayúsculas y minúsculas', () => {
    for (const t of ['Fernando Alonso', 'fERNANDO aLONSO', 'FERNANDO   ALONSO', 'fernando alonso!']) expect(detectarHuevo(t)).toBe('victoria')
  })
  it('lo reconoce como expresión completa dentro de una frase', () => {
    for (const t of ['Hola, Fernando Alonso ganó', 'viva fernando alonso']) expect(detectarHuevo(t)).toBe('victoria')
  })
  it('no se activa dentro de otras palabras ni con el apellido suelto', () => {
    for (const t of ['fernandoalonso', 'fernando alonsos', 'mifernando alonso', 'alonso', 'fernando']) expect(detectarHuevo(t)).toBeNull()
  })
  it('no se activa con textos normales', () => {
    for (const t of ['convierte 67 USD a euros', '2 + 67', 'qué hora es?', '']) expect(detectarHuevo(t)).toBeNull()
  })
})
