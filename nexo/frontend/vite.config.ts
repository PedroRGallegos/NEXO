import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// En desarrollo, /api se redirige al backend (python main_web.py) y no hace falta CORS.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
  test: { environment: 'node' },
})
