#!/bin/bash
# SkillForge Development Environment Setup Script
# Issue #69: Create Setup Script
#
# This script sets up the entire development environment with one command:
# - Checks for Docker installation
# - Creates .env file from .env.example (if missing)
# - Starts Docker services (PostgreSQL + Backend)
# - Waits for PostgreSQL to be ready
# - Installs Python dependencies using Poetry
# - Runs database migrations
# - Verifies API key configuration

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

info "Setting up SkillForge development environment..."
echo ""

# Step 1: Check Docker installation
info "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    error "Docker not found. Please install Docker first."
    echo "  Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Determine which Docker Compose command to use
DOCKER_COMPOSE_CMD=""
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    error "Docker Compose not found. Please install Docker Compose."
    exit 1
fi

success "Docker and Docker Compose are installed"
echo ""

# Step 2: Create .env file from .env.example (if missing)
info "Checking for .env file..."
if [ ! -f "$BACKEND_DIR/.env" ]; then
    if [ ! -f "$BACKEND_DIR/.env.example" ]; then
        error ".env.example not found at $BACKEND_DIR/.env.example"
        exit 1
    fi
    info "Creating .env file from .env.example..."
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    success ".env file created"
    warning "Please update $BACKEND_DIR/.env with your API keys"
else
    success ".env file already exists (skipping creation)"
fi
echo ""

# Step 3: Start Docker services
info "Starting Docker services..."
cd "$PROJECT_ROOT"
if $DOCKER_COMPOSE_CMD ps | grep -q "skillforge-postgres-dev.*Up"; then
    success "Docker services already running"
else
    $DOCKER_COMPOSE_CMD up -d
    success "Docker services started"
fi
echo ""

# Step 4: Wait for PostgreSQL to be ready
info "Waiting for PostgreSQL to be ready..."
MAX_WAIT=60
WAIT_COUNT=0
while ! $DOCKER_COMPOSE_CMD exec -T postgres pg_isready -U dev &> /dev/null; do
    if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
        error "PostgreSQL did not become ready within $MAX_WAIT seconds"
        error "Check logs with: $DOCKER_COMPOSE_CMD logs postgres"
        exit 1
    fi
    sleep 2
    WAIT_COUNT=$((WAIT_COUNT + 2))
    echo -n "."
done
echo ""
success "PostgreSQL is ready"
echo ""

# Step 5: Check Poetry installation
info "Checking Poetry installation..."
if ! command -v poetry &> /dev/null; then
    error "Poetry not found. Please install Poetry first."
    echo "  Install with: curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi
success "Poetry is installed"
echo ""

# Step 6: Install Python dependencies
info "Installing Python dependencies with Poetry..."
cd "$BACKEND_DIR"
poetry install --no-interaction
success "Python dependencies installed"
echo ""

# Step 7: Run database migrations
info "Running database migrations..."
poetry run alembic upgrade head
success "Database migrations completed"
echo ""

# Step 8: Verify API key configuration
info "Verifying API key configuration..."

# Source .env file to read variables
if [ -f "$BACKEND_DIR/.env" ]; then
    # Read LLM_MODEL from .env (default to gpt-5-mini if not set)
    LLM_MODEL=$(grep -E "^LLM_MODEL=" "$BACKEND_DIR/.env" | cut -d '=' -f2 | tr -d '"' | tr -d "'" || echo "gpt-5-mini")
    if [ -z "$LLM_MODEL" ] || [ "$LLM_MODEL" = "" ]; then
        LLM_MODEL="gpt-5-mini"
    fi
    
    # Determine required API key based on LLM_MODEL
    REQUIRED_API_KEY=""
    API_KEY_NAME=""
    
    if [[ "$LLM_MODEL" == gpt* ]] || [[ "$LLM_MODEL" == *gpt* ]]; then
        REQUIRED_API_KEY=$(grep -E "^OPENAI_API_KEY=" "$BACKEND_DIR/.env" | cut -d '=' -f2 | tr -d '"' | tr -d "'" || echo "")
        API_KEY_NAME="OPENAI_API_KEY"
    elif [[ "$LLM_MODEL" == claude* ]] || [[ "$LLM_MODEL" == *claude* ]]; then
        REQUIRED_API_KEY=$(grep -E "^ANTHROPIC_API_KEY=" "$BACKEND_DIR/.env" | cut -d '=' -f2 | tr -d '"' | tr -d "'" || echo "")
        API_KEY_NAME="ANTHROPIC_API_KEY"
    elif [[ "$LLM_MODEL" == gemini* ]] || [[ "$LLM_MODEL" == *gemini* ]]; then
        REQUIRED_API_KEY=$(grep -E "^GOOGLE_API_KEY=" "$BACKEND_DIR/.env" | cut -d '=' -f2 | tr -d '"' | tr -d "'" || echo "")
        API_KEY_NAME="GOOGLE_API_KEY"
    elif [[ "$LLM_MODEL" == grok* ]] || [[ "$LLM_MODEL" == *grok* ]]; then
        REQUIRED_API_KEY=$(grep -E "^XAI_API_KEY=" "$BACKEND_DIR/.env" | cut -d '=' -f2 | tr -d '"' | tr -d "'" || echo "")
        API_KEY_NAME="XAI_API_KEY"
    elif [[ "$LLM_MODEL" == deepseek* ]] || [[ "$LLM_MODEL" == *deepseek* ]]; then
        REQUIRED_API_KEY=$(grep -E "^DEEPSEEK_API_KEY=" "$BACKEND_DIR/.env" | cut -d '=' -f2 | tr -d '"' | tr -d "'" || echo "")
        API_KEY_NAME="DEEPSEEK_API_KEY"
    else
        # Default to OpenAI for unknown models
        REQUIRED_API_KEY=$(grep -E "^OPENAI_API_KEY=" "$BACKEND_DIR/.env" | cut -d '=' -f2 | tr -d '"' | tr -d "'" || echo "")
        API_KEY_NAME="OPENAI_API_KEY"
    fi
    
    # Check required API key
    if [ -z "$REQUIRED_API_KEY" ] || [ "$REQUIRED_API_KEY" = "" ]; then
        warning "$API_KEY_NAME is not set in .env file (required for LLM_MODEL=$LLM_MODEL)"
        warning "  Get your API key and add it to $BACKEND_DIR/.env"
    else
        success "$API_KEY_NAME is configured"
    fi
    
    # Check JINA_API_KEY (optional)
    JINA_API_KEY=$(grep -E "^JINA_API_KEY=" "$BACKEND_DIR/.env" | cut -d '=' -f2 | tr -d '"' | tr -d "'" || echo "")
    if [ -z "$JINA_API_KEY" ] || [ "$JINA_API_KEY" = "" ]; then
        warning "JINA_API_KEY is not set in .env file (optional, but recommended for content extraction)"
        warning "  Get free key at: https://jina.ai"
    else
        success "JINA_API_KEY is configured"
    fi
else
    warning "Could not read .env file for API key verification"
fi
echo ""

# Step 9: Success message
success "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Update $BACKEND_DIR/.env with your API keys (if not already done)"
echo "  2. Start the backend server:"
echo "     cd $BACKEND_DIR"
echo "     poetry run uvicorn app.main:app --reload"
echo "  3. Visit http://localhost:8500/docs for API documentation"
echo ""
echo "Useful commands:"
echo "  - View logs: $DOCKER_COMPOSE_CMD logs -f backend"
echo "  - Stop services: $DOCKER_COMPOSE_CMD down"
echo "  - Restart services: $DOCKER_COMPOSE_CMD restart"





