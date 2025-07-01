import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    host: '0.0.0.0',
    port: 3000,
    hmr: false,
    proxy: {
      '/api': {
        target: process.env.VITE_BACKEND_URL || 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      },
      '/api/v1/ws': {
        target: process.env.VITE_BACKEND_WS_URL || 'ws://localhost:8000',
        ws: true,
        changeOrigin: true
      }
    }
  },
  build: {
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['echarts']
        }
      }
    }
  },
  css: {
    devSourcemap: true
  },
  optimizeDeps: {
    include: ['echarts']
  }
})