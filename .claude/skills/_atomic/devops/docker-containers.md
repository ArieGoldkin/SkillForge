---
name: docker-containers
description: Docker multi-stage builds and image optimization
version: 1.0.0
tags: [docker, containers, optimization, security]
size: atomic
domain: devops
---

# Docker Containers

## Multi-Stage Build

```dockerfile
# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# Stage 2: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 3: Production
FROM node:20-alpine AS runner
WORKDIR /app

# Security: Non-root user
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001

COPY --from=deps --chown=nodejs:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=nodejs:nodejs /app/dist ./dist

USER nodejs
EXPOSE 3000
ENV NODE_ENV=production
HEALTHCHECK --interval=30s CMD node healthcheck.js || exit 1
CMD ["node", "dist/main.js"]
```

**Size**: 850MB → 180MB (78% reduction)

## Layer Caching

```dockerfile
# ❌ BAD: Invalidates cache on code change
COPY . .
RUN npm install

# ✅ GOOD: Cache package.json separately
COPY package*.json ./
RUN npm ci
COPY . .
```

## Security Hardening

```dockerfile
# Non-root user
USER 1001

# Read-only filesystem
# (set in Kubernetes securityContext)

# Drop capabilities
# (set in Kubernetes securityContext)
```

## Docker Compose (Dev)

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    ports: ["5437:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready"]
      interval: 5s

  backend:
    build: ./backend
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./backend:/app  # Hot reload
```
