/* Voz simulada de NEXO: convierte el texto de la respuesta en un nivel de «volumen» que sube y baja
   con el ritmo del habla (una subida por sílaba, silencios en las comas y los puntos). No hay audio:
   es la animación de la esfera la que «habla» al ritmo del texto que llega por streaming. */

export interface Unidad {
  tipo: 'silaba' | 'pausa'
  duracion: number // segundos a velocidad normal
  amplitud: number // 0..1
}

const GRUPO = /(\d+(?:[.,]\d+)*)|([aeiouáéíóúüàèìò]+)|([.!?…]+)|([,;:]+)|(\n+)/gi
const FUERZA_VOCAL: Record<string, number> = { a: 1, o: 0.95, e: 0.9, u: 0.72, i: 0.66 }
const SEGUNDOS_OBJETIVO_MAX = 4 // si hay mucho texto pendiente, se habla más deprisa para no ir por detrás
const VELOCIDAD_MAX = 6

function base(letra: string): number {
  return FUERZA_VOCAL[letra.normalize('NFD')[0]] ?? 0.8
}

/** Texto -> sílabas y pausas. Determinista: el mismo texto da siempre el mismo ritmo. */
export function trocear(texto: string): Unidad[] {
  const unidades: Unidad[] = []
  for (const m of texto.matchAll(GRUPO)) {
    const [trozo, numero, vocales, fuerte, suave, salto] = m
    const variacion = 0.86 + 0.14 * (((trozo.charCodeAt(0) * 7 + trozo.length * 3) % 10) / 10)
    if (numero) {
      const cifras = Math.min(6, numero.replace(/\D/g, '').length)
      for (let i = 0; i < cifras; i++) unidades.push({ tipo: 'silaba', duracion: 0.15, amplitud: 0.8 * variacion })
    } else if (vocales) {
      const acento = /[áéíóú]/i.test(vocales) ? 0.1 : 0
      unidades.push({ tipo: 'silaba', duracion: 0.14 + 0.02 * (vocales.length % 3), amplitud: Math.min(1, base(vocales[0].toLowerCase()) * variacion + acento) })
    } else if (fuerte) {
      unidades.push({ tipo: 'pausa', duracion: 0.38, amplitud: 0 })
    } else if (suave) {
      unidades.push({ tipo: 'pausa', duracion: 0.17, amplitud: 0 })
    } else if (salto) {
      unidades.push({ tipo: 'pausa', duracion: 0.3, amplitud: 0 })
    }
  }
  return unidades
}

export class GeneradorVoz {
  /** Nivel suavizado, de 0 (silencio) a 1. */
  nivel = 0
  /** Sube en uno cada vez que empieza una sílaba (para lanzar una onda). */
  contador = 0
  ultimaAmplitud = 0

  private cola: Unidad[] = []
  private actual: Unidad | null = null
  private transcurrido = 0
  private segundosEnCola = 0

  /** Añade el texto nuevo que llega (un fragmento del streaming). */
  empujar(texto: string): void {
    for (const unidad of trocear(texto)) {
      this.cola.push(unidad)
      this.segundosEnCola += unidad.duracion
    }
  }

  /** Corta la voz al instante (conversación nueva o petición nueva). */
  reiniciar(): void {
    this.cola = []
    this.actual = null
    this.transcurrido = 0
    this.segundosEnCola = 0
    this.nivel = 0
  }

  get activa(): boolean {
    return this.cola.length > 0 || this.actual !== null || this.nivel > 0.02
  }

  /** Tiempo que falta para terminar de «decir» lo que hay en cola, ya con la velocidad ajustada. */
  segundosPendientes(): number {
    const restante = this.segundosEnCola + (this.actual ? this.actual.duracion - this.transcurrido : 0)
    return restante / this.velocidad(restante)
  }

  private velocidad(pendiente: number): number {
    return Math.min(VELOCIDAD_MAX, Math.max(1, pendiente / SEGUNDOS_OBJETIVO_MAX))
  }

  /** Avanza ``dt`` segundos y devuelve el nivel actual. */
  avanzar(dt: number): number {
    let objetivo = 0
    let disponible = dt * this.velocidad(this.segundosEnCola + (this.actual ? this.actual.duracion : 0))
    while (disponible > 0) {
      if (!this.actual) {
        this.actual = this.cola.shift() ?? null
        if (!this.actual) break
        this.segundosEnCola = Math.max(0, this.segundosEnCola - this.actual.duracion)
        this.transcurrido = 0
        if (this.actual.tipo === 'silaba') {
          this.contador += 1
          this.ultimaAmplitud = this.actual.amplitud
        }
      }
      const falta = this.actual.duracion - this.transcurrido
      const paso = Math.min(disponible, falta)
      this.transcurrido += paso
      disponible -= paso
      if (this.actual.tipo === 'silaba') {
        const u = Math.min(1, this.transcurrido / this.actual.duracion)
        objetivo = this.actual.amplitud * Math.pow(Math.sin(Math.PI * u), 0.6)
      }
      if (this.transcurrido >= this.actual.duracion - 1e-9) this.actual = null
    }
    this.nivel += (objetivo - this.nivel) * (1 - Math.exp(-dt * 28)) // ataque y caída suaves
    if (this.nivel < 0.004) this.nivel = 0
    return this.nivel
  }
}
