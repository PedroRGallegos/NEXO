import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './estilos/base.css'
import './estilos/layout.css'
import './estilos/componentes.css'
import './estilos/cyberpunk.css'
import './estilos/responsive.css'

createRoot(document.getElementById('raiz')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
