import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Backend runs behind the nginx gateway on http://localhost:80.
// Proxy API paths server-side so the browser stays same-origin:
// no CORS, and (critically) no preflight that the gateway's auth_request would 401.
const API_TARGET = process.env.VITE_API_TARGET || 'http://localhost'
const apiPaths = ['/auth', '/upload', '/generate-exam', '/submit-answer', '/history', '/get-exam', '/health', '/enrich']

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: Object.fromEntries(
      apiPaths.map((p) => [p, { target: API_TARGET, changeOrigin: true }]),
    ),
  },
})
