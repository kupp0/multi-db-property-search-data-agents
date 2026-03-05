import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    fs: {
      allow: ['..']
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
        secure: false,
      },
      '/agent': {
        target: 'http://127.0.0.1:8083',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/agent/, ''),
      },
    },
  },
})