# SkillForge Frontend

SkillForge frontend (React 19 + Vite + TypeScript) with **TanStack Router**, **TanStack Query**, **Zustand**, and Tailwind.

**Source of truth for ports/env vars:** `../docs/CONFIGURATION.md`

---

## 🚀 Quick start

### Prerequisites
- Node.js 20+

### Install
```bash
cd frontend
npm install
```

### Configure
```bash
# frontend/.env.local
VITE_API_URL=http://localhost:8500
```

### Run
```bash
npm run dev
```

Then open:
- Frontend: `http://localhost:5173`
- Backend (Swagger): `http://localhost:8500/docs`

---

## 🧪 Tests & quality

```bash
# Unit tests
npm test

# E2E tests (Playwright)
npm run test:e2e

# Lint + format + typecheck
npm run quality:check
```

---

## 🧭 Architecture & code layout

- Frontend architecture doc: `../docs/FRONTEND_ARCHITECTURE.md`
- Feature-based modules live under `src/features/`
- Routes are file-based via TanStack Router (`src/routes/`)
- Backend integration lives in `src/services/` (see `src/services/api.service.ts`)

