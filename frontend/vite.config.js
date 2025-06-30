import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    // Use environment variables to determine host and port for container compatibility
    host: process.env.CONTAINER_FRONTEND_HOST || 'localhost',
    port: parseInt(process.env.CONTAINER_FRONTEND_PORT || '3000'),
    // Enable hot module replacement in containers
    hmr: {
      port: parseInt(process.env.CONTAINER_FRONTEND_PORT || '3000')
    },
    // Watch options for better container performance
    watch: {
      usePolling: true,
      interval: 100
    }
  },
  // Ensure proper base path for container deployment
  base: '/',
  // Build configuration for production
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: true
  }
})