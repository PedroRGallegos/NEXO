import type { Modelo } from './api/tipos'

/** Un modelo es remoto si el servidor lo dice, o (servidor antiguo) si es `llm`. */
export function esRemoto(m: Modelo): boolean {
  if (m.tipo !== undefined && m.tipo !== null) return m.tipo === 'remoto'
  return m.id === 'llm'
}

/** Sin campo `disponible` (servidor antiguo) se considera disponible. */
export function estaDisponible(m: Modelo): boolean {
  return m.disponible !== false
}

/** Separa los modelos en locales y remotos conservando el orden original. */
export function agruparModelos(modelos: Modelo[]): { locales: Modelo[]; remotos: Modelo[] } {
  const locales: Modelo[] = []
  const remotos: Modelo[] = []
  for (const m of modelos) (esRemoto(m) ? remotos : locales).push(m)
  return { locales, remotos }
}
