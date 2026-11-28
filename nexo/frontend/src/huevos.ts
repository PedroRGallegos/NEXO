/** Easter eggs: cada uno es una entrada del registro. Añadir otro = añadir una definición aquí
 *  (y su ilustración en components/Huevo.tsx). La detección no depende de React. */
export type Huevo = 'victoria'

interface Definicion {
  id: Huevo
  /** Recibe el texto normalizado: minúsculas, sin tildes y con signos convertidos en espacios. */
  coincide: (normalizado: string) => boolean
}

export const normalizar = (texto: string) =>
  texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()

const FRASE_ALONSO = /(?:^| )fernando alonso(?: |$)/

const REGISTRO: readonly Definicion[] = [
  { id: 'victoria', coincide: (n) => FRASE_ALONSO.test(n) },
]

export function detectarHuevo(texto: string): Huevo | null {
  const n = normalizar(texto)
  return REGISTRO.find((d) => d.coincide(n))?.id ?? null
}
