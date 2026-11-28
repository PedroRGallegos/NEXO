/** Comandos de texto del chat que NEXO atiende en la interfaz, sin enviarlos al agente. */
const LIMPIAR = new Set(['/limpiar', '/clear'])

/** `/limpiar` (o `/clear`): empieza una conversación en blanco; la anterior sigue en el historial. */
export function esComandoLimpiar(texto: string): boolean {
  return LIMPIAR.has(texto.trim().toLowerCase())
}
