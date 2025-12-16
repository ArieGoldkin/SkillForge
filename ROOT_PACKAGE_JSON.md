# Root package.json Purpose

This `package.json` at the repository root is for **workspace-level tooling**, not application dependencies.

## Purpose

- **Context Bridge**: Syncs context between Claude sessions via `.claude/scripts/context-bridge.js`
- **Husky**: Git hooks for pre-commit validation
- **Lint-staged**: Runs linters on staged files before commit

## Dependencies

- `chokidar`: File watching for context bridge
- `husky`: Git hooks manager
- `lint-staged`: Staged file linting

## Note

The frontend application has its own `package.json` in `frontend/` with React, Vite, and other frontend dependencies.

This root `package.json` is **separate** and serves workspace management purposes only.

