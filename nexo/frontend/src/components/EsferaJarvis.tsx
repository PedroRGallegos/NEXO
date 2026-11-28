import { useEffect, useRef } from 'react'
import type { GeneradorVoz } from '../voz'
import '../estilos/esfera.css'

export type EstadoEsfera = 'espera' | 'pensando' | 'hablando'

interface Props {
  estado: EstadoEsfera
  /** Voz simulada: mientras tiene texto en cola la esfera «habla» al ritmo de las sílabas. */
  voz?: GeneradorVoz
}

/* Esfera holográfica generada por código (diseño propio): partículas y trazos en capa esférica,
   anillos fragmentados, marcas de escala, núcleo con filamentos y chispas. Todo se proyecta en 3D
   con una rotación sencilla y se dibuja con mezcla aditiva sobre un canvas 2D transparente. */

const TAU = Math.PI * 2
const N_PARTICULAS = 1700
const N_RADIALES = 70
const N_CHISPAS = 46
const DPR_MAX = 2
const LADO_MAX = 900 // píxeles de respaldo máximos del canvas
const COLORES = ['rgba(139, 92, 246,', 'rgba(0, 128, 255,', 'rgba(221, 214, 254,', 'rgba(90,225,255,']

/** Parámetros que cambian con el estado; se interpolan para que las transiciones sean suaves. */
interface Parametros {
  velocidad: number
  brillo: number
  expansion: number
  vibracion: number
  chispas: number
  estela: number // 0..1: cuánto se desvanece cada fotograma (más alto = menos estela)
  latido: number
  voz: number // nivel de voz 0..1 (lo fija la propia animación en cada fotograma, no se interpola)
}
const OBJETIVO: Record<EstadoEsfera, Parametros> = {
  espera: { velocidad: 1, brillo: 0.85, expansion: 1, vibracion: 0, chispas: 0.08, estela: 0.5, latido: 0.35, voz: 0 },
  pensando: { velocidad: 3.2, brillo: 1.05, expansion: 0.95, vibracion: 0.012, chispas: 0.7, estela: 0.32, latido: 1.1, voz: 0 },
  hablando: { velocidad: 1.8, brillo: 1.3, expansion: 1.06, vibracion: 0.05, chispas: 0.35, estela: 0.4, latido: 1.8, voz: 0 },
}

/** Onda de sonido: un círculo que se expande desde la esfera y se desvanece. */
interface Onda {
  edad: number
  amplitud: number
}
const VIDA_ONDA = 0.9
const MAX_ONDAS = 6
const N_BARRAS = 72

interface Anillo {
  radio: number
  inclX: number
  inclZ: number
  velocidad: number
  grosor: number
  color: number
  segmentos: [number, number][] // [ángulo inicial, longitud] en radianes
}

function aleatorioSemilla(semilla: number) {
  let s = semilla >>> 0
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0
    return s / 4294967296
  }
}

function crearEscena() {
  const azar = aleatorioSemilla(20261127)
  const bx = new Float32Array(N_PARTICULAS), by = new Float32Array(N_PARTICULAS), bz = new Float32Array(N_PARTICULAS)
  const tx = new Float32Array(N_PARTICULAS), ty = new Float32Array(N_PARTICULAS), tz = new Float32Array(N_PARTICULAS)
  const largo = new Float32Array(N_PARTICULAS), fase = new Float32Array(N_PARTICULAS)
  const clase = new Uint8Array(N_PARTICULAS)

  for (let i = 0; i < N_PARTICULAS; i++) {
    const tipo = azar()
    let lon = azar() * TAU
    let y: number
    let radio = 0.9 + azar() * 0.1
    let sobreMeridiano = false
    if (tipo < 0.3) {
      y = Math.sin(((Math.floor(azar() * 9) - 4) / 4.4) * 1.15) + (azar() - 0.5) * 0.02 // bandas de latitud
    } else if (tipo < 0.45) {
      y = azar() * 2 - 1
      lon = Math.floor(azar() * 12) * (TAU / 12) + (azar() - 0.5) * 0.03 // meridianos
      sobreMeridiano = true
    } else if (tipo < 0.78) {
      y = azar() * 2 - 1
    } else {
      y = azar() * 2 - 1
      radio = 0.3 + Math.cbrt(azar()) * 0.55 // volumen interior, más tenue
    }
    const sec = Math.sqrt(Math.max(0, 1 - y * y))
    const x = Math.cos(lon) * sec
    const z = Math.sin(lon) * sec
    bx[i] = x * radio; by[i] = y * radio; bz[i] = z * radio
    // Tangente: a lo largo de la longitud (bandas) o de la latitud (meridianos).
    let ux: number, uy: number, uz: number
    if (sobreMeridiano) { ux = -y * Math.cos(lon); uy = sec; uz = -y * Math.sin(lon) } else { ux = -Math.sin(lon); uy = 0; uz = Math.cos(lon) }
    const mod = Math.hypot(ux, uy, uz) || 1
    tx[i] = ux / mod; ty[i] = uy / mod; tz[i] = uz / mod
    largo[i] = azar() < 0.7 ? 0.006 + azar() * 0.02 : 0.04 + azar() * 0.09
    fase[i] = azar() * TAU
    clase[i] = radio < 0.86 ? 0 : azar() < 0.1 ? 3 : azar() < 0.25 ? 2 : azar() < 0.6 ? 1 : 0
  }

  const rx = new Float32Array(N_RADIALES * 3), rl = new Float32Array(N_RADIALES * 2)
  for (let i = 0; i < N_RADIALES; i++) {
    const y = azar() * 2 - 1, lon = azar() * TAU, sec = Math.sqrt(1 - y * y)
    rx[i * 3] = Math.cos(lon) * sec; rx[i * 3 + 1] = y; rx[i * 3 + 2] = Math.sin(lon) * sec
    rl[i * 2] = 0.34 + azar() * 0.3
    rl[i * 2 + 1] = rl[i * 2] + 0.05 + azar() * 0.28
  }

  const anillos: Anillo[] = [
    { radio: 1.06, inclX: 1.2, inclZ: 0.25, velocidad: 0.22, grosor: 1.6, color: 1, segmentos: [] },
    { radio: 0.97, inclX: 0.5, inclZ: -0.7, velocidad: -0.34, grosor: 1.2, color: 0, segmentos: [] },
    { radio: 0.74, inclX: 1.45, inclZ: 1.0, velocidad: 0.5, grosor: 1.1, color: 2, segmentos: [] },
    { radio: 0.56, inclX: 0.9, inclZ: -0.2, velocidad: -0.8, grosor: 1, color: 3, segmentos: [] },
    { radio: 1.16, inclX: 1.35, inclZ: 0.0, velocidad: 0.1, grosor: 0.9, color: 0, segmentos: [] },
  ]
  for (const anillo of anillos) {
    let a = azar() * TAU
    while (a < TAU * 2) {
      const longitud = 0.18 + azar() * 0.9
      if (a < TAU) anillo.segmentos.push([a, longitud])
      a += longitud + 0.12 + azar() * 0.5
    }
  }

  return { bx, by, bz, tx, ty, tz, largo, fase, clase, rx, rl, anillos }
}

function dibujar(
  ctx: CanvasRenderingContext2D,
  escena: ReturnType<typeof crearEscena>,
  lado: number,
  dpr: number,
  t: number,
  p: Parametros,
  chispas: Float32Array,
  limpiar: boolean,
  ondas: Onda[] = [],
) {
  const { bx, by, bz, tx, ty, tz, largo, fase, clase, rx, rl, anillos } = escena
  const c = lado / 2
  const latido = 1 + 0.012 * p.latido * Math.sin(t * (2 + p.latido * 2))
  const voz = p.voz
  const R = c * 0.78 * p.expansion * latido * (1 + 0.06 * voz)
  const yaw = t * 0.16 * p.velocidad
  const cy_ = Math.cos(yaw), sy_ = Math.sin(yaw)
  const cp = Math.cos(0.38), sp = Math.sin(0.38)

  if (limpiar) {
    ctx.globalCompositeOperation = 'destination-out'
    ctx.fillStyle = `rgba(0,0,0,${p.estela})`
    ctx.fillRect(0, 0, lado, lado)
  } else {
    ctx.clearRect(0, 0, lado, lado)
  }
  ctx.globalCompositeOperation = 'lighter'
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'

  // Proyección: rotación Y (yaw) + inclinación X fija + perspectiva ligera.
  let sx = 0, sy = 0, sz = 0
  const proyectar = (x: number, y: number, z: number, escala: number) => {
    const x1 = x * cy_ + z * sy_
    const z1 = -x * sy_ + z * cy_
    const y2 = y * cp - z1 * sp
    const z2 = y * sp + z1 * cp
    const f = (1 + z2 * 0.16) * escala
    sx = c + x1 * R * f
    sy = c + y2 * R * f
    sz = z2
  }

  const brillo = p.brillo * (1 + 0.4 * voz)

  // 1) Partículas y trazos, agrupados por color y por cara (delantera/trasera) para trazar en bloques.
  const vib = p.vibracion + 0.035 * voz
  for (let cara = 0; cara < 2; cara++) {
    for (let k = 0; k < 4; k++) {
      ctx.beginPath()
      for (let i = 0; i < N_PARTICULAS; i++) {
        if (clase[i] !== k) continue
        const despl = vib ? 1 + vib * Math.sin(t * 9 + fase[i] * 3) : 1
        const l = largo[i]
        proyectar(bx[i] * despl, by[i] * despl, bz[i] * despl, 1)
        if ((sz > 0 ? 1 : 0) !== cara) continue
        const x0 = sx, y0 = sy
        proyectar((bx[i] + tx[i] * l) * despl, (by[i] + ty[i] * l) * despl, (bz[i] + tz[i] * l) * despl, 1)
        ctx.moveTo(x0, y0)
        ctx.lineTo(sx + 0.01, sy)
      }
      const alfa = (cara ? 0.55 : 0.2) * brillo * (k === 3 ? 0.55 : 1)
      ctx.strokeStyle = `${COLORES[k]}${Math.min(1, alfa)})`
      ctx.lineWidth = (cara ? 1.35 : 0.9) * dpr
      ctx.stroke()
    }
  }

  // 2) Trazos radiales desde el núcleo (rayos de luz).
  ctx.beginPath()
  for (let i = 0; i < N_RADIALES; i++) {
    const ux = rx[i * 3], uy = rx[i * 3 + 1], uz = rx[i * 3 + 2]
    const pulso = 1 + 0.04 * p.latido * Math.sin(t * 3 + i)
    proyectar(ux * rl[i * 2] * pulso, uy * rl[i * 2] * pulso, uz * rl[i * 2] * pulso, 1)
    const x0 = sx, y0 = sy
    proyectar(ux * rl[i * 2 + 1] * pulso, uy * rl[i * 2 + 1] * pulso, uz * rl[i * 2 + 1] * pulso, 1)
    ctx.moveTo(x0, y0)
    ctx.lineTo(sx, sy)
  }
  ctx.strokeStyle = `rgba(139, 92, 246,${0.14 * brillo})`
  ctx.lineWidth = 0.8 * dpr
  ctx.stroke()

  // 3) Anillos fragmentados con marcas de escala.
  for (let r = 0; r < anillos.length; r++) {
    const an = anillos[r]
    const giro = t * an.velocidad * p.velocidad
    const cx_ = Math.cos(an.inclX), sx_ = Math.sin(an.inclX), cz = Math.cos(an.inclZ), sz_ = Math.sin(an.inclZ)
    const punto = (ang: number, radio: number) => {
      const x = Math.cos(ang) * radio, y = Math.sin(ang) * radio
      const y1 = y * cx_, z1 = y * sx_ // inclinación sobre X
      proyectar(x * cz - y1 * sz_, x * sz_ + y1 * cz, z1, 1)
    }
    ctx.beginPath()
    for (const [a0, len] of an.segmentos) {
      const pasos = Math.max(2, Math.ceil(len / 0.1))
      for (let s = 0; s <= pasos; s++) {
        punto(a0 + giro + (len * s) / pasos, an.radio)
        if (s === 0) ctx.moveTo(sx, sy)
        else ctx.lineTo(sx, sy)
      }
    }
    ctx.strokeStyle = `${COLORES[an.color]}${Math.min(1, 0.5 * brillo)})`
    ctx.lineWidth = an.grosor * dpr
    ctx.stroke()

    if (r === 0 || r === 4) { // regla de marcas en el anillo exterior
      ctx.beginPath()
      const marcas = r === 0 ? 96 : 60
      for (let m = 0; m < marcas; m++) {
        const ang = (m / marcas) * TAU - giro * 0.6
        const mayor = m % 5 === 0
        punto(ang, an.radio + 0.025)
        const x0 = sx, y0 = sy
        punto(ang, an.radio + (mayor ? 0.075 : 0.045))
        ctx.moveTo(x0, y0)
        ctx.lineTo(sx, sy)
      }
      ctx.strokeStyle = `rgba(167, 139, 250,${0.32 * brillo})`
      ctx.lineWidth = 0.9 * dpr
      ctx.stroke()
    }
  }

  // 3b) Elipses de órbita tenues (muestran el volumen).
  ctx.beginPath()
  for (let o = 0; o < 3; o++) {
    const giro = t * (0.1 + o * 0.04) * p.velocidad
    const inc = 0.4 + o * 0.55
    for (let s = 0; s <= 72; s++) {
      const ang = (s / 72) * TAU + giro
      const x = Math.cos(ang) * 0.9, y = Math.sin(ang) * 0.9
      proyectar(x * Math.cos(o * 1.1) - y * Math.cos(inc) * Math.sin(o * 1.1), x * Math.sin(o * 1.1) + y * Math.cos(inc) * Math.cos(o * 1.1), y * Math.sin(inc), 1)
      if (s % 6 < 4) { if (s % 6 === 0) ctx.moveTo(sx, sy); else ctx.lineTo(sx, sy) }
    }
  }
  ctx.strokeStyle = `rgba(139, 92, 246,${0.2 * brillo})`
  ctx.lineWidth = 0.8 * dpr
  ctx.stroke()

  // 4) Núcleo: resplandor, filamentos en espiral y punto central.
  const pulsoNucleo = 0.85 + 0.15 * Math.sin(t * (2.6 + p.latido)) * p.latido + 0.7 * voz
  const rNucleo = R * (0.2 + 0.06 * pulsoNucleo * p.brillo)
  const g = ctx.createRadialGradient(c, c, 0, c, c, rNucleo * 1.9)
  g.addColorStop(0, `rgba(237, 233, 254,${Math.min(1, 0.5 * p.brillo)})`)
  g.addColorStop(0.3, `rgba(139, 92, 246,${0.22 * p.brillo})`)
  g.addColorStop(1, 'rgba(0, 128, 255,0)')
  ctx.fillStyle = g
  ctx.beginPath()
  ctx.arc(c, c, rNucleo * 1.9, 0, TAU)
  ctx.fill()

  for (let f = 0; f < 3; f++) {
    ctx.beginPath()
    const fase0 = (f / 3) * TAU + t * (1.2 + f * 0.3) * p.velocidad
    for (let s = 0; s <= 40; s++) {
      const u = s / 40
      const ang = fase0 + u * TAU * 1.6
      const rad = 0.03 + u * 0.27 * (0.9 + 0.1 * Math.sin(t * 3 + f))
      proyectar(Math.cos(ang) * rad, (u - 0.5) * 0.1 * Math.sin(t + f), Math.sin(ang) * rad, 1)
      if (s === 0) ctx.moveTo(sx, sy)
      else ctx.lineTo(sx, sy)
    }
    ctx.strokeStyle = `rgba(147, 197, 253,${0.55 * brillo})`
    ctx.lineWidth = 1.1 * dpr
    ctx.stroke()
  }
  ctx.fillStyle = `rgba(255,250,226,${Math.min(1, 0.85 * brillo)})`
  ctx.beginPath()
  ctx.arc(c, c, Math.max(1.5, R * 0.018) * dpr * 0.8 + pulsoNucleo * 1.5, 0, TAU)
  ctx.fill()

  // 4b) Voz: ondas de sonido que salen de la esfera y anillo ecualizador que reacciona al nivel.
  if (ondas.length) {
    for (const onda of ondas) {
      const u = onda.edad / VIDA_ONDA
      ctx.beginPath()
      ctx.arc(c, c, R * (1.03 + u * 0.2), 0, TAU)
      ctx.strokeStyle = `rgba(147, 197, 253,${Math.max(0, (1 - u) * 0.5 * onda.amplitud)})`
      ctx.lineWidth = (1.8 - u * 1.2) * dpr
      ctx.stroke()
    }
  }
  if (voz > 0.015) {
    ctx.beginPath()
    const interior = R * 1.1
    for (let i = 0; i < N_BARRAS; i++) {
      const ang = (i / N_BARRAS) * TAU + t * 0.25
      const espectro = 0.5 + 0.5 * Math.sin(t * 11 + i * 1.7) * Math.sin(t * 7.3 + i * 0.61)
      const largoBarra = R * (0.01 + 0.115 * voz * (0.25 + 0.75 * espectro)) // cabe dentro del lienzo
      const co = Math.cos(ang), si = Math.sin(ang)
      ctx.moveTo(c + co * interior, c + si * interior)
      ctx.lineTo(c + co * (interior + largoBarra), c + si * (interior + largoBarra))
    }
    ctx.strokeStyle = `rgba(90,225,255,${Math.min(1, 0.25 + 0.65 * voz)})`
    ctx.lineWidth = 1.8 * dpr
    ctx.stroke()
  }

  // 5) Chispas: partículas que salen del núcleo; la cantidad depende del estado.
  ctx.beginPath()
  for (let i = 0; i < N_CHISPAS; i++) {
    const o = i * 5 // [vida, x, y, z, velocidad]
    if (chispas[o] <= 0) continue
    const d = chispas[o + 4]
    proyectar(chispas[o + 1] * d, chispas[o + 2] * d, chispas[o + 3] * d, 1)
    ctx.moveTo(sx, sy)
    ctx.lineTo(sx + 0.01, sy)
  }
  ctx.strokeStyle = `rgba(224, 231, 255,${0.85 * Math.min(1, brillo)})`
  ctx.lineWidth = 2.1 * dpr
  ctx.stroke()
}

function avanzarChispas(chispas: Float32Array, dt: number, tasa: number) {
  let nuevas = tasa * 60 * dt
  for (let i = 0; i < N_CHISPAS; i++) {
    const o = i * 5
    if (chispas[o] > 0) {
      chispas[o] -= dt * 0.7
      chispas[o + 4] += dt * (0.5 + chispas[o + 4] * 0.4)
    } else if (nuevas > 0 && Math.random() < Math.min(1, nuevas)) {
      nuevas -= 1
      const y = Math.random() * 2 - 1, lon = Math.random() * TAU, sec = Math.sqrt(1 - y * y)
      chispas[o] = 0.6 + Math.random() * 0.8
      chispas[o + 1] = Math.cos(lon) * sec
      chispas[o + 2] = y
      chispas[o + 3] = Math.sin(lon) * sec
      chispas[o + 4] = 0.12
    }
    if (chispas[o + 4] > 1.1) chispas[o] = 0
  }
}

const DESCRIPCION: Record<EstadoEsfera, string> = {
  espera: 'Esfera holográfica de NEXO en reposo',
  pensando: 'Esfera holográfica de NEXO analizando la petición',
  hablando: 'Esfera holográfica de NEXO respondiendo',
}

export function EsferaJarvis({ estado, voz }: Props) {
  const lienzo = useRef<HTMLCanvasElement>(null)
  const estadoRef = useRef(estado)
  const vozRef = useRef(voz)
  vozRef.current = voz
  const redibujar = useRef<(() => void) | null>(null)

  useEffect(() => {
    estadoRef.current = estado
    redibujar.current?.() // con movimiento reducido repinta el fotograma estático con el nuevo estado
  }, [estado])

  useEffect(() => {
    const canvas = lienzo.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return

    const escena = crearEscena()
    const chispas = new Float32Array(N_CHISPAS * 5)
    const ondas: Onda[] = []
    let contadorVisto = vozRef.current?.contador ?? 0
    const parametros: Parametros = { ...OBJETIVO[estadoRef.current] }
    const reducido = window.matchMedia('(prefers-reduced-motion: reduce)')
    let lado = 0
    let dpr = 1
    let t = 0
    let ultimo = 0
    let cuadro: number | null = null
    let enPantalla = true

    const ajustar = () => {
      dpr = Math.min(DPR_MAX, window.devicePixelRatio || 1)
      lado = Math.round(Math.min(LADO_MAX, canvas.clientWidth * dpr))
      if (lado < 8) return
      canvas.width = lado
      canvas.height = lado
      pintarEstatico()
    }

    const pintarEstatico = () => {
      if (!reducido.matches || lado < 8) return
      Object.assign(parametros, OBJETIVO[estadoRef.current], { vibracion: 0, estela: 1, voz: 0 })
      dibujar(ctx, escena, lado, dpr, 3.2, parametros, chispas, false)
    }
    redibujar.current = pintarEstatico

    const interpolar = (dt: number) => {
      const meta = vozRef.current?.activa ? OBJETIVO.hablando : OBJETIVO[estadoRef.current]
      const k = 1 - Math.exp(-dt * 4)
      for (const clave of Object.keys(meta) as (keyof Parametros)[]) {
        parametros[clave] += (meta[clave] - parametros[clave]) * k
      }
    }

    const bucle = (ahora: number) => {
      cuadro = null
      // Tope de fotogramas: 20/s en reposo y 30/s si hay actividad (menos CPU sin perder fluidez).
      const intervaloMinimo = estadoRef.current === 'espera' && !vozRef.current?.activa ? 1000 / 20 : 1000 / 30
      if (ultimo && ahora - ultimo < intervaloMinimo - 2) {
        programar()
        return
      }
      const dt = Math.min(0.05, ultimo ? (ahora - ultimo) / 1000 : 0.016)
      ultimo = ahora
      t += dt
      interpolar(dt)
      const generador = vozRef.current
      if (generador) {
        parametros.voz = generador.avanzar(dt)
        if (generador.contador !== contadorVisto) {
          contadorVisto = generador.contador
          if (generador.ultimaAmplitud > 0.6 && ondas.length < MAX_ONDAS) ondas.push({ edad: 0, amplitud: generador.ultimaAmplitud })
        }
      } else {
        parametros.voz = 0
      }
      for (let i = ondas.length - 1; i >= 0; i--) {
        ondas[i].edad += dt
        if (ondas[i].edad > VIDA_ONDA) ondas.splice(i, 1)
      }
      avanzarChispas(chispas, dt, parametros.chispas)
      dibujar(ctx, escena, lado, dpr, t, parametros, chispas, true, ondas)
      programar()
    }

    const deberiaAnimar = () => !reducido.matches && enPantalla && document.visibilityState === 'visible' && lado >= 8
    const programar = () => {
      if (cuadro === null && deberiaAnimar()) cuadro = window.requestAnimationFrame(bucle)
    }
    const parar = () => {
      if (cuadro !== null) window.cancelAnimationFrame(cuadro)
      cuadro = null
      ultimo = 0
    }
    const evaluar = () => {
      if (deberiaAnimar()) programar()
      else parar()
    }

    const observadorTamano = new ResizeObserver(() => { ajustar(); evaluar() })
    const observadorVisible = new IntersectionObserver(([entrada]) => {
      enPantalla = entrada.isIntersecting
      evaluar()
    })
    observadorTamano.observe(canvas)
    observadorVisible.observe(canvas)
    document.addEventListener('visibilitychange', evaluar)
    const alCambiarMovimiento = () => {
      if (reducido.matches) {
        parar()
        pintarEstatico()
      } else {
        ctx.clearRect(0, 0, lado, lado)
        evaluar()
      }
    }
    reducido.addEventListener('change', alCambiarMovimiento)
    ajustar()
    evaluar()

    return () => {
      parar()
      observadorTamano.disconnect()
      observadorVisible.disconnect()
      document.removeEventListener('visibilitychange', evaluar)
      reducido.removeEventListener('change', alCambiarMovimiento)
      redibujar.current = null
    }
  }, [])

  return <canvas ref={lienzo} className="esfera-jarvis" role="img" aria-label={DESCRIPCION[estado]} />
}
