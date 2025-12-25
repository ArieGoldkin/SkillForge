import path from 'path'

import { tanstackRouter } from '@tanstack/router-plugin/vite'
import react from '@vitejs/plugin-react'
import { visualizer } from 'rollup-plugin-visualizer'
import { defineConfig, type PluginOption } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [
    tanstackRouter(), // Must come before react plugin
    react(),
    // Bundle analysis - only in analyze mode
    mode === 'analyze' &&
      (visualizer({
        filename: 'bundle-stats.html',
        open: true,
        gzipSize: true,
        brotliSize: true,
        template: 'treemap',
      }) as PluginOption),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@features': path.resolve(__dirname, './src/features'),
      '@shared': path.resolve(__dirname, './src/shared'),
      '@stores': path.resolve(__dirname, './src/stores'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@app-types': path.resolve(__dirname, './src/types'),
      '@lib': path.resolve(__dirname, './src/lib'),
      '@services': path.resolve(__dirname, './src/services'),
      '@router': path.resolve(__dirname, './src/router'),
    },
  },
  server: {
    port: 5173, // SkillForge dev port
    strictPort: true,
    allowedHosts: ['host.docker.internal', 'localhost'], // Allow Playwright MCP access
    proxy: {
      '/api': {
        target: 'http://localhost:8500',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    // Warn when chunk size exceeds 500KB
    chunkSizeWarningLimit: 500,
    rollupOptions: {
      output: {
        // Strategic chunk splitting for optimal caching
        manualChunks: {
          // Core React - rarely changes
          'react-vendor': ['react', 'react-dom'],
          // Router - own chunk for route-based splitting
          router: ['@tanstack/react-router'],
          // Data fetching - shared across features
          query: ['@tanstack/react-query'],
          // UI components - large but shared
          ui: ['framer-motion', 'lucide-react'],
          // Markdown rendering - only loaded when needed
          markdown: ['react-markdown'],
        },
      },
    },
  },
}))
