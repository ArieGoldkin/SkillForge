# Multi-stage build for SkillForge Frontend
# Note: Each stage runs its own `npm ci` to ensure platform-specific native binaries
# are installed correctly. This fixes the Rollup linux-x64/arm64 issue.
# See: https://github.com/npm/cli/issues/4828

# Stage 1: Development (for hot-reload)
FROM node:20-slim AS development

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
# Note: npm ci has a bug with optional platform-specific binaries (https://github.com/npm/cli/issues/4828)
# Workaround: reinstall packages with native binaries to ensure platform-specific versions are installed
RUN npm ci && npm install rollup lightningcss --force

# Copy source files
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Run development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

# Stage 2: Builder (for production)
FROM node:20-slim AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies with native binary fix (rollup, lightningcss)
RUN npm ci && npm install rollup lightningcss --force

# Copy source files
COPY . .

# Build the application
RUN npm run build

# Stage 3: Production (nginx for static files)
FROM nginx:alpine AS production

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config if needed
# COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

# Stage 4: E2E Testing (with Playwright)
FROM mcr.microsoft.com/playwright:v1.57.0-jammy AS e2e

WORKDIR /app

# Copy package files and install with native binary fix
COPY package.json package-lock.json ./
RUN npm ci && npm install rollup lightningcss --force

# Copy source and test files
COPY . .

# Default command runs E2E tests
CMD ["npx", "playwright", "test", "--project=chromium"]
