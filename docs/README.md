# 📚 SkillForge Documentation

This folder contains the canonical project documentation. If you see conflicting ports, URLs, or environment variable names in other docs, treat **`docs/CONFIGURATION.md`** as the source of truth.

---

## 🚀 Start here (choose your path)

### If you want to use SkillForge (high-level)
- **Project overview**: `../README.md`
- **Current status**: `CURRENT_STATUS.md`
- **Roadmap**: `ROADMAP.md`

### If you want to contribute (setup + architecture)
- **Configuration (ports/env vars)**: `CONFIGURATION.md`
- **Architecture + diagrams**: `ARCHITECTURE.md`
- **Integration contracts (REST + SSE)**: `INTEGRATION_POINTS.md`
- **Frontend architecture**: `FRONTEND_ARCHITECTURE.md`

---

## 🧠 Key system flows (where to look)

- **Analysis pipeline**: start at `ARCHITECTURE.md` → “Backend Workflow” + “Integration Flow”
- **SSE event schema**: `issues/040-sse-endpoint/SSE_SCHEMA.md`
- **Search (full-text / semantic / hybrid)**: `issues/075-fulltext-search/`
- **E2E infra (Playwright)**: see repo root `PLAN_E2E_FIXES.md` and `frontend/e2e/`

---

## ✅ Documentation conventions

- **Do not hardcode ports** in multiple places. Link to `CONFIGURATION.md`.
- **Mermaid diagrams** should avoid HTML (`<br/>`) and custom `style` blocks to keep rendering stable.


