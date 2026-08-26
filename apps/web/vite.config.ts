/// <reference types="vitest/config" />
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// NOTE: `defineConfig` is imported from 'vitest/config', not 'vite'. Vite's own
// export has no `test` key in its type, so the config below fails to typecheck
// against it even though it runs fine.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    // Proxy /api to the backend so the browser never needs a CORS preflight and
    // the frontend never needs to know the API's address. In Docker this
    // resolves to the `api` service; locally, to localhost.
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
  },
})
