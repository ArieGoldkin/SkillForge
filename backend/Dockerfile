# Multi-stage build for SkillForge Backend
# Stage 1: Builder
FROM python:3.13-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_VERSION=1.8.3 \
    POETRY_HOME=/opt/poetry \
    POETRY_VENV=/opt/poetry-venv \
    POETRY_CACHE_DIR=/opt/.cache

RUN python3 -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/pip install -U pip setuptools \
    && $POETRY_VENV/bin/pip install poetry==${POETRY_VERSION}

ENV PATH="${PATH}:${POETRY_VENV}/bin"

# Set work directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Configure Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/opt/.cache

# Install dependencies (without dev dependencies for production)
RUN poetry install --only=main --no-root && \
    poetry export -f requirements.txt --output requirements.txt --without-hashes

# Stage 2: Runtime
FROM python:3.13-slim as runtime

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY app/ ./app/
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Copy requirements for reference (not used in runtime, but useful for debugging)
COPY --from=builder /app/requirements.txt ./

# Set Python path
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8500

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8500/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8500"]
