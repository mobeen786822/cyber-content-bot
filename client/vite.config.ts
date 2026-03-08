import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => ({
  plugins: [react(), tailwindcss()],
  server: mode === 'development'
    ? {
        proxy: {
          '/status': { target: 'http://localhost:5058', changeOrigin: true },
          '/run': { target: 'http://localhost:5058', changeOrigin: true },
          '/draft': { target: 'http://localhost:5058', changeOrigin: true },
        },
      }
    : undefined,
}))
