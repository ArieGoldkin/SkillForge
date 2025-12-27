#!/usr/bin/env node
/**
 * Bundle Size Checker
 *
 * Enforces bundle size budgets in CI. Fails if any chunk exceeds its limit.
 *
 * Usage: node scripts/check-bundle-size.js
 *
 * Issue #552: Bundle Analysis Tooling for Size Monitoring
 */

import { readdirSync, statSync } from 'fs'
import { join } from 'path'
import { fileURLToPath } from 'url'
import { dirname } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// Bundle size budgets (in KB)
// These are enforced in CI - prevent regressions from current baseline
// Budgets set at current size + 15% headroom for minor changes
// Updated: Dec 2025 based on actual build output
const BUDGETS = {
  // Core vendor chunks
  'react-vendor': 15,     // React + ReactDOM (~11KB currently)
  'router': 90,           // TanStack Router (~75KB currently)
  'query': 45,            // TanStack Query (~35KB currently)
  'ui': 150,              // Framer Motion + Lucide (~126KB currently)
  'markdown': 135,        // React Markdown (~115KB currently)

  // Main app bundle - WARNING: This is large and should be reduced
  // TODO: Code split with React.lazy() to reduce this below 500KB
  'index': 1500,          // Main entry (~1.26MB currently - needs optimization)

  // Total budget for all JS (including mermaid diagrams)
  // Current: 3.73MB - includes many lazy-loaded diagram renderers
  TOTAL: 4500,            // 4.5MB total (3.73MB current + headroom)
}

// ANSI colors for terminal output
const colors = {
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  reset: '\x1b[0m',
  bold: '\x1b[1m',
}

function formatSize(bytes) {
  const kb = bytes / 1024
  if (kb >= 1024) {
    return `${(kb / 1024).toFixed(2)} MB`
  }
  return `${kb.toFixed(2)} KB`
}

function getChunkName(filename) {
  // Extract chunk name from filename like "react-vendor-abc123.js"
  const match = filename.match(/^(.+?)-[a-zA-Z0-9]+\.js$/)
  if (match) {
    return match[1]
  }
  // Handle index-abc123.js
  if (filename.startsWith('index-')) {
    return 'index'
  }
  return null
}

function checkBundleSizes() {
  const distPath = join(__dirname, '..', 'dist', 'assets')

  console.log(`\n${colors.bold}📦 Bundle Size Check${colors.reset}\n`)
  console.log(`Checking: ${distPath}\n`)

  let files
  try {
    files = readdirSync(distPath)
  } catch (error) {
    console.error(`${colors.red}Error: dist/assets not found. Run 'npm run build' first.${colors.reset}`)
    process.exit(1)
  }

  const jsFiles = files.filter(f => f.endsWith('.js'))
  const results = []
  let totalSize = 0
  let hasErrors = false

  for (const file of jsFiles) {
    const filePath = join(distPath, file)
    const stats = statSync(filePath)
    const sizeKB = stats.size / 1024
    totalSize += stats.size

    const chunkName = getChunkName(file)
    const budget = chunkName ? BUDGETS[chunkName] : null

    let status = '✓'
    let color = colors.green

    if (budget && sizeKB > budget) {
      status = '✗'
      color = colors.red
      hasErrors = true
    } else if (budget && sizeKB > budget * 0.9) {
      status = '⚠'
      color = colors.yellow
    }

    results.push({
      file,
      chunkName,
      size: stats.size,
      sizeKB,
      budget,
      status,
      color,
    })
  }

  // Sort by size descending
  results.sort((a, b) => b.size - a.size)

  // Print results table
  console.log(`${'File'.padEnd(40)} ${'Size'.padStart(12)} ${'Budget'.padStart(12)} Status`)
  console.log('─'.repeat(72))

  for (const r of results) {
    const budgetStr = r.budget ? `${r.budget} KB` : '-'
    console.log(
      `${r.color}${r.file.padEnd(40)} ${formatSize(r.size).padStart(12)} ${budgetStr.padStart(12)} ${r.status}${colors.reset}`
    )
  }

  console.log('─'.repeat(72))

  // Check total budget
  const totalKB = totalSize / 1024
  const totalStatus = totalKB > BUDGETS.TOTAL ? '✗' : '✓'
  const totalColor = totalKB > BUDGETS.TOTAL ? colors.red : colors.green

  if (totalKB > BUDGETS.TOTAL) {
    hasErrors = true
  }

  console.log(
    `${totalColor}${'TOTAL'.padEnd(40)} ${formatSize(totalSize).padStart(12)} ${`${BUDGETS.TOTAL} KB`.padStart(12)} ${totalStatus}${colors.reset}`
  )

  console.log()

  if (hasErrors) {
    console.log(`${colors.red}${colors.bold}❌ Bundle size check FAILED${colors.reset}`)
    console.log(`${colors.red}Some chunks exceed their budget. Consider:`)
    console.log(`  - Code splitting with React.lazy()`)
    console.log(`  - Moving large dependencies to separate chunks`)
    console.log(`  - Tree-shaking unused exports`)
    console.log(`  - Updating budgets if the increase is justified${colors.reset}\n`)
    process.exit(1)
  } else {
    console.log(`${colors.green}${colors.bold}✅ Bundle size check PASSED${colors.reset}\n`)
  }
}

checkBundleSizes()
