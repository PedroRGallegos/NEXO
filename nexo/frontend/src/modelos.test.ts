import { describe, expect, it } from 'vitest'
import { agruparModelos, estaDisponible } from './modelos'
import type { Modelo } from './api/tipos'

const reglas: Modelo = { id: 'reglas', nombre: 'ModeloReglas', tipo: 'local', disponible: true, motivo: null, detalle: null }
const eco: Modelo = { id: 'eco', nombre: 'ModeloEco', tipo: 'local', disponible: true, motivo: null, detalle: null }
const llmNo: Modelo = { id: 'llm', nombre: 'ModeloLLM', tipo: 'remoto', disponible: false, motivo: 'Configura LLM_API_KEY en el archivo .env del servidor.', detalle: null }
const llmSi: Modelo = { id: 'llm', nombre: 'ModeloLLM', tipo: 'remoto', disponible: true, motivo: null, detalle: 'gpt-4o' }

describe('agruparModelos', () => {
  it('mantiene el orden: reglas y eco juntos, llm aparte', () => {
    const g = agruparModelos([reglas, llmNo, eco])
    expect(g.locales.map((m) => m.id)).toEqual(['reglas', 'eco'])
    expect(g.remotos.map((m) => m.id)).toEqual(['llm'])
  })

  it('servidor antiguo sin campos: locales y disponibles, llm remoto', () => {
    const g = agruparModelos([
      { id: 'reglas', nombre: 'ModeloReglas' },
      { id: 'eco', nombre: 'ModeloEco' },
      { id: 'llm', nombre: 'ModeloLLM' },
    ])
    expect(g.locales).toHaveLength(2)
    expect(g.remotos).toHaveLength(1)
    expect(g.remotos[0].id).toBe('llm')
    expect(estaDisponible(g.locales[0])).toBe(true)
    expect(estaDisponible(g.remotos[0])).toBe(true)
  })

  it('llm no disponible: sigue en remotos y no está disponible', () => {
    const g = agruparModelos([reglas, eco, llmNo])
    expect(g.remotos).toHaveLength(1)
    expect(estaDisponible(g.remotos[0])).toBe(false)
    expect(g.remotos[0].motivo).toBe('Configura LLM_API_KEY en el archivo .env del servidor.')
  })

  it('llm disponible: disponible y con detalle', () => {
    const g = agruparModelos([reglas, eco, llmSi])
    expect(estaDisponible(g.remotos[0])).toBe(true)
    expect(g.remotos[0].detalle).toBe('gpt-4o')
  })

  it('lista vacía: dos grupos vacíos', () => {
    const g = agruparModelos([])
    expect(g.locales).toHaveLength(0)
    expect(g.remotos).toHaveLength(0)
  })
})
