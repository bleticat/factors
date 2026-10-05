import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Sidesteps CORS during dev by forwarding to the FastAPI backend
      // (see backend/factors/main.py — CORS is also configured there for
      // direct calls, e.g. from tests or non-proxied tooling).
      //
      // Defaults to 127.0.0.1 for running the frontend directly on the
      // host; docker-compose.yml overrides VITE_PROXY_TARGET to
      // http://backend:8000 since containers reach each other by service
      // name, not localhost.
      '/api': {
        target: process.env.VITE_PROXY_TARGET ?? 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
