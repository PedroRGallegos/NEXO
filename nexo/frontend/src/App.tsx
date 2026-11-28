import { useCallback, useState } from 'react'
import { Huevo } from './components/Huevo'
import { detectarHuevo, type Huevo as TipoHuevo } from './huevos'
import { Chat } from './components/Chat'
import { PanelConfig } from './components/PanelConfig'
import { PanelStats } from './components/PanelStats'
import { Sidebar } from './components/Sidebar'
import { useChat } from './hooks/useChat'
import { esComandoLimpiar } from './comandos'

export type Panel = 'config' | 'stats' | null

export default function App() {
  const chat = useChat()
  const [panel, setPanel] = useState<Panel>(null)
  const [menuAbierto, setMenuAbierto] = useState(false)
  const [huevo, setHuevo] = useState<TipoHuevo | null>(null)
  const cerrarHuevo = useCallback(() => setHuevo(null), [])

  const alternar = (p: Exclude<Panel, null>) => setPanel((actual) => (actual === p ? null : p))
  const elegirConversacion = (accion: () => void) => () => {
    accion()
    setMenuAbierto(false)
  }

  return (
    <div className={`app${panel ? ' app--con-panel' : ''}`}>
      <Sidebar
        conversaciones={chat.conversaciones}
        activaId={chat.activa?.id ?? null}
        hayConversacionVacia={chat.mensajes.length === 0}
        conectado={chat.conectado}
        panel={panel}
        abierto={menuAbierto}
        onNueva={elegirConversacion(() => void chat.nueva())}
        onAbrir={(id) => elegirConversacion(() => void chat.abrir(id))()}
        onPanel={(p) => {
          alternar(p)
          setMenuAbierto(false)
        }}
        onCerrar={() => setMenuAbierto(false)}
      />
      <Chat
        conversacion={chat.activa}
        mensajes={chat.mensajes}
        enviando={chat.enviando}
        error={chat.error}
        onEnviar={(t) => {
          if (esComandoLimpiar(t)) {
            void chat.limpiar()
            return
          }
          setHuevo(detectarHuevo(t))
          void chat.enviar(t)
        }}
        onDescartarError={chat.descartarError}
        onMenu={() => setMenuAbierto(true)}
        conectado={chat.conectado}
        aviso={chat.aviso}
      />
      {panel === 'config' && (
        <PanelConfig modeloActual={chat.activa?.modelo ?? null} onModelo={(m) => void chat.cambiarModelo(m)} onCerrar={() => setPanel(null)} />
      )}
      {huevo && <Huevo tipo={huevo} onTerminar={cerrarHuevo} />}
      {panel === 'stats' && <PanelStats version={chat.version} onCerrar={() => setPanel(null)} />}
    </div>
  )
}
