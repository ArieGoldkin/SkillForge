import path from 'path'

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    typecheck: {
      tsconfig: './tsconfig.test.json',
    },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'json-summary', 'html', 'lcov'],
      reportsDirectory: './coverage',
      exclude: [
        'node_modules/',
        'src/**/*.d.ts',
        'src/**/*.test.{ts,tsx}',
        'src/**/__tests__/**/*.test.{ts,tsx}',
        'src/test-utils/',
      ],
      thresholds: {
        global: {
          branches: 80,
          functions: 80,
          lines: 80,
          statements: 80,
        },
        // Component-specific thresholds
        './src/features/': {
          branches: 85,
          functions: 85,
          lines: 85,
        },
        // Critical business logic
        './src/shared/services/': {
          branches: 90,
          functions: 90,
        },
      },
      reportOnFailure: true, // Fail CI if coverage drops
    },

    // Environment-aware timeouts
    testTimeout: process.env.CI ? 10000 : 5000,

    // Smart retry for flaky tests
    retry: process.env.CI ? 2 : 0,
    // Test tagging system (2025 best practices)
    // Exclude E2E tests by default unless E2E_READY=true
    testNamePattern: process.env.E2E_READY === 'true' ? undefined : /^(?!.*@component-e2e).*$/,
    tags: {
      // Test Types (Primary categorization)
      e2e: ['@e2e'],              // End-to-end user workflows
      integration: ['@integration'], // API/Database integration tests
      unit: ['@unit'],            // Pure unit tests (no external deps)

      // Execution Context (Secondary categorization)
      ci: ['@ci'],                // Critical CI tests (always run)
      dev: ['@dev'],              // Development-only tests
      manual: ['@manual'],        // Requires manual setup/intervention

      // Performance & Reliability
      slow: ['@slow'],            // Performance-impacting tests (>2s)
      flaky: ['@flaky'],          // Known unreliable tests
      critical: ['@critical'],    // Mission-critical functionality

      // Feature States
      experimental: ['@experimental'], // New/unstable features
      deprecated: ['@deprecated'], // Legacy functionality to be removed

      // Component Types
      component: ['@component'],  // UI component tests
      hook: ['@hook'],            // Custom hook tests
      store: ['@store'],          // State management tests
      util: ['@util'],            // Utility function tests
    },
    // Performance monitoring setup
    performance: {
      // Enable performance monitoring in tests
      enabled: true,
      // Report performance regressions
      reportOnFailure: true,
    },
  },
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
      '@test-utils': path.resolve(__dirname, './src/test-utils'),
      '@components': path.resolve(__dirname, './src/components'),
    },
  },
})
