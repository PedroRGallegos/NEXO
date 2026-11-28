/** Imágenes en el chat. El servidor escribe ``[[imagen:/sorpresas/archivo.jpg]]`` y aquí se convierte en una foto.
 *  Solo se aceptan rutas de la carpeta pública /sorpresas/: el texto de un mensaje nunca puede cargar una URL externa. */
const MARCA = /\[\[imagen:([^\]]*)\]\]/
const MARCA_SIN_CERRAR = /\[\[imagen:[^\]]*$/ // por si el streaming entrega la marca partida
const RUTA_VALIDA = /^\/sorpresas\/[a-z0-9-]+\.(?:jpg|png|webp)$/

const DESCRIPCION: Record<string, string> = {
  '/sorpresas/fernando-alonso.jpg': 'Fernando Alonso',
}

export interface ContenidoConImagen {
  texto: string
  imagen?: { ruta: string; descripcion: string }
}

export function separarImagen(contenido: string): ContenidoConImagen {
  const encontrada = MARCA.exec(contenido)
  const sinMarca = contenido.replace(MARCA, '').replace(MARCA_SIN_CERRAR, '').trim()
  const ruta = encontrada?.[1]
  if (!ruta || !RUTA_VALIDA.test(ruta)) return { texto: encontrada ? sinMarca : contenido.replace(MARCA_SIN_CERRAR, '').trim() }
  return { texto: sinMarca, imagen: { ruta, descripcion: DESCRIPCION[ruta] ?? 'Imagen' } }
}
