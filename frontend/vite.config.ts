/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: true,
    port: 5173,
    allowedHosts: ['datamonster', 'datamonster.tailce7f83.ts.net'],
    proxy: {
      '/api': {
        target: process.env.VITE_PROXY_API_URL || 'http://backend:8000',
        changeOrigin: true,
      },
      '/health': {
        target: process.env.VITE_PROXY_API_URL || 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/__tests__/setup.ts',
    css: false,
    exclude: ['e2e/**', 'node_modules/**'],
  },
})
