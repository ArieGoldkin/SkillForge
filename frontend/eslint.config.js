// For more info, see https://github.com/storybookjs/eslint-plugin-storybook#configuration-flat-config-format
import storybook from "eslint-plugin-storybook";

import js from '@eslint/js'
import globals from 'globals'
import react from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import importPlugin from 'eslint-plugin-import'

export default tseslint.config(// Global ignores
{
  ignores: [
    'dist',
    'node_modules',
    'build',
    '.next',
    'coverage',
    '../.claude/**',
    '../.squad/**',
  ],
}, // Recommended configs
js.configs.recommended, ...tseslint.configs.recommended, // Custom configuration
{
  files: ['**/*.{ts,tsx}'],
  languageOptions: {
    ecmaVersion: 2022,
    globals: globals.browser,
    parserOptions: {
      ecmaFeatures: {
        jsx: true,
      },
    },
  },
  plugins: {
    react: react,
    'react-hooks': reactHooks,
    'react-refresh': reactRefresh,
    import: importPlugin,
  },
  rules: {
    // React rules
    'react/no-array-index-key': 'error',

    // React Hooks rules
    ...reactHooks.configs.recommended.rules,
    'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],

    // Code Quality - File and Function Limits
    'max-lines': [
      'error',
      {
        max: 180,
        skipBlankLines: true,
        skipComments: true,
      },
    ],
    'max-lines-per-function': [
      'error',
      {
        max: 50,
        skipBlankLines: true,
        skipComments: true,
      },
    ],
    complexity: ['error', 15],
    'max-depth': ['error', 4],
    'max-params': ['error', 4],

    // Best Practices
    'no-console': ['warn', { allow: ['warn', 'error'] }],
    'prefer-const': 'error',
    'no-var': 'error',
    'no-unused-vars': 'off', // Use TypeScript's no-unused-vars instead
    '@typescript-eslint/no-unused-vars': [
      'error',
      {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
      },
    ],
    '@typescript-eslint/explicit-function-return-type': 'off', // Too strict for React components
    '@typescript-eslint/explicit-module-boundary-types': 'off',

    // Import Rules
    'import/order': [
      'error',
      {
        groups: ['builtin', 'external', 'internal', 'parent', 'sibling', 'index'],
        pathGroups: [
          {
            pattern: 'react',
            group: 'builtin',
            position: 'before',
          },
          {
            pattern: '@/**',
            group: 'internal',
          },
          {
            pattern: '@features/**',
            group: 'internal',
            position: 'after',
          },
          {
            pattern: '@shared/**',
            group: 'internal',
            position: 'after',
          },
          {
            pattern: '@store/**',
            group: 'internal',
            position: 'after',
          },
          {
            pattern: '@types/**',
            group: 'internal',
            position: 'after',
          },
          {
            pattern: '@lib/**',
            group: 'internal',
            position: 'after',
          },
          {
            pattern: '@services/**',
            group: 'internal',
            position: 'after',
          },
        ],
        pathGroupsExcludedImportTypes: ['react'],
        'newlines-between': 'always',
        alphabetize: {
          order: 'asc',
          caseInsensitive: true,
        },
      },
    ],
    'import/no-duplicates': 'error',
    'import/no-unresolved': 'off', // TypeScript handles this
    'import/first': 'error',
    'import/newline-after-import': 'error',
  },
}, // Relaxed rules for example/showcase files and layout components
{
  files: ['**/examples/**/*.tsx', '**/design-system/example.tsx', '**/AppShell.tsx'],
  rules: {
    'max-lines': 'off',
    'max-lines-per-function': 'off',
  },
}, // Relaxed rules for shadcn/ui components (they export variants by design)
{
  files: ['**/components/ui/**/*.tsx'],
  rules: {
    'react-refresh/only-export-components': 'off',
  },
}, // Relaxed rules for test files and test utilities
{
  files: [
    '**/*.test.ts',
    '**/*.test.tsx',
    '**/__tests__/**/*.ts',
    '**/__tests__/**/*.tsx',
    '**/test-utils/**/*.ts',
    '**/test-utils/**/*.tsx',
    '**/e2e/**/*.ts', // E2E tests and utilities need console for debugging/reporting
  ],
  rules: {
    'max-lines': 'off',
    'max-lines-per-function': 'off',
    'no-console': 'off', // Test utilities need console for debugging/reporting
  },
}, // Relaxed rules for performance monitoring (needs console.log for metrics)
{
  files: ['**/services/performance/**/*.ts'],
  rules: {
    'no-console': 'off',
  },
}, // Relaxed rules for constants file (comprehensive constants organization)
{
  files: ['**/lib/constants.ts'],
  rules: {
    'max-lines': ['error', { max: 500, skipBlankLines: true, skipComments: true }],
  },
}, // Relaxed rules for status/display components (legitimate complex switch statements)
{
  files: ['**/components/**/ConnectionStatus.tsx', '**/components/**/AnalysisTab.tsx'],
  rules: {
    'max-lines-per-function': ['error', { max: 70, skipBlankLines: true, skipComments: true }],
  },
}, // Relaxed rules for store helper files (complex state management utilities)
{
  files: ['**/stores/*StoreHelpers.ts'],
  rules: {
    'max-lines': ['error', { max: 300, skipBlankLines: true, skipComments: true }],
    'max-lines-per-function': ['error', { max: 70, skipBlankLines: true, skipComments: true }],
    'no-console': 'off', // Store helpers need console for debugging connection issues
  },
}, // Relaxed rules for SSE hooks (need console for connection debugging)
{
  files: ['**/hooks/useSSE.ts'],
  rules: {
    'no-console': 'off',
  },
}, // Relaxed rules for app entry point (dev-only initialization logging)
{
  files: ['**/main.tsx'],
  rules: {
    'no-console': 'off',
  },
}, // Relaxed rules for main store files (Zustand stores with state + actions + selectors)
{
  files: ['**/stores/*Store.ts'],
  rules: {
    'max-lines': ['error', { max: 200, skipBlankLines: true, skipComments: true }],
  },
}, storybook.configs["flat/recommended"]);
