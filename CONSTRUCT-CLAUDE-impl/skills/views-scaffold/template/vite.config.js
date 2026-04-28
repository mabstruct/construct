import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: '../build',
    emptyOutDir: false
  },
  server: {
    port: 5173,
    open: false
  }
})
