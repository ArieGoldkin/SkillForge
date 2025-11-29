# Deployment Strategy: Vercel + Railway + Supabase

**Version:** 1.0  
**Date:** January 2026  
**Status:** Approved - Option 2

## Architecture Overview

**Selected Stack:**
- **Frontend:** Vercel (React 19 static deployment)
- **Backend:** Railway (FastAPI Python 3.13)
- **Database:** Supabase PostgreSQL with PGVector

**Why This Combination:**
- Vercel: Best-in-class React deployment with CDN and automatic previews
- Railway: Simple, developer-friendly FastAPI hosting with persistent connections
- Supabase: Managed PostgreSQL with PGVector, excellent developer experience

**Estimated Monthly Cost:** $15-30 (depending on usage and Supabase tier)

---

## Quick Reference

### Frontend (Vercel)
- **URL:** https://vercel.com
- **Project:** `skillforge-production`
- **Root Directory:** `frontend`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`

### Backend (Railway)
- **URL:** https://railway.app
- **Service:** `skillforge-backend`
- **Root Directory:** `backend`
- **Build Command:** `poetry install --no-dev`
- **Start Command:** `poetry run uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Database (Supabase)
- **URL:** https://supabase.com/dashboard
- **Project:** `skillforge-production`
- **Connection:** Transaction Mode pooler (for Railway)
- **Extension:** PGVector enabled

---

## Detailed Documentation

For complete deployment instructions, see:
- **Full Deployment Guide:** This document (comprehensive steps)
- **GitHub Issues:** All deployment tasks in Sprint 7 milestone
- **Architecture:** `docs/ARCHITECTURE.md` - Deployment Architecture section

---

## Key Configuration

### Environment Variables

**Railway (Backend):**
- `DATABASE_URL` - Supabase connection string (Transaction Mode)
- `OPENAI_API_KEY` - LLM API key
- `JINA_API_KEY` - Content extraction API key
- `ENVIRONMENT=production`
- `CORS_ORIGINS` - Vercel domain(s)

**Vercel (Frontend):**
- `VITE_API_BASE_URL` - Railway backend URL

### Connection Strings

**Supabase (Transaction Mode Pooler):**
```
postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?pgbouncer=true
```

**SQLAlchemy (with asyncpg):**
```
postgresql+asyncpg://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?pgbouncer=true
```

---

## Deployment Workflow

1. **Database Setup:** Create Supabase project, enable PGVector
2. **Backend Deployment:** Deploy to Railway, configure environment variables
3. **Frontend Deployment:** Deploy to Vercel, configure API URL
4. **Testing:** End-to-end verification of all components
5. **Monitoring:** Set up health checks, error tracking, uptime monitoring

---

## Related Issues

All deployment tasks are tracked in GitHub Issues under **Sprint 7: Testing & Deployment** milestone:
- Database setup and configuration
- Railway backend deployment
- Vercel frontend deployment
- End-to-end testing
- Monitoring and logging
- Deployment runbook

---

## References

- **Railway Docs:** https://docs.railway.app
- **Vercel Docs:** https://vercel.com/docs
- **Supabase Docs:** https://supabase.com/docs
- **Full Plan:** See deployment plan document for complete details
