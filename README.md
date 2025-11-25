# 🚀 SkillForge

> **Intelligent Learning Integration Platform** - Analyze technical content, generate actionable implementation guides, and learn through Socratic tutoring.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![React](https://img.shields.io/badge/React-19.0-61dafb.svg)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.121-009688.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.0-orange.svg)](https://github.com/langchain-ai/langgraph)
[![Python](https://img.shields.io/badge/Python-3.13-3776ab.svg)](https://python.org)

---

## 📚 Documentation

- **[Architecture](docs/ARCHITECTURE.md)** - System architecture diagrams
- **[Roadmap](docs/ROADMAP.md)** - Project roadmap and phases
- **[Integration Points](docs/INTEGRATION_POINTS.md)** - API contracts & coordination
- **[User Stories](docs/USER_STORIES.md)** - User stories with acceptance criteria
- **[Current Status](docs/CURRENT_STATUS.md)** - Current project status
- **[Issues Documentation](docs/issues/README.md)** - Issue-specific documentation
- **[Backend Tasks](docs/YONATAN_BACKEND_TASKS.md)** - Backend task breakdown
- **[Frontend Tasks](docs/ARIE_FRONTEND_TASKS.md)** - Frontend task breakdown

---

## 📖 What is SkillForge?

SkillForge is a research-to-implementation pipeline that helps developers:

1. **📊 Analyze technical content** from URLs (articles, videos, GitHub repos)
2. **🤖 Generate AI-ready artifacts** optimized for Claude Code, Cursor, and other AI coding assistants
3. **🎓 Learn through Socratic tutoring** with interactive dialogue
4. **📚 Build a searchable knowledge library** of analyzed content

### Use Cases

- **Learning new technologies:** Analyze tutorials and get step-by-step implementation guides
- **Technical research:** Compare frameworks, assess integration feasibility, identify security implications
- **Codebase integration:** Generate prompts to help AI coding assistants implement new patterns
- **Knowledge management:** Build a searchable library of technical learnings

---

## ✨ Key Features

### 🔍 Multi-Agent Analysis Pipeline

- **8 specialized AI agents** analyze content in parallel:
  - Tech Comparator
  - Integration Feasibility Checker
  - Security Auditor
  - Performance Analyst
  - Code Quality Critic
  - Trend Validator
  - Implementation Planner
  - Dependency Mapper

### 📄 Smart Artifact Generation

- **Comprehensive markdown files** with:
  - Executive summaries
  - Technical comparisons
  - Step-by-step implementation plans
  - Ready-to-use prompts for AI coding assistants
  - Code examples and best practices

### 🎓 Interactive Tutoring

- **Socratic dialogue** adapts to your understanding level
- Learn concepts deeply through guided questions
- Context-aware explanations using analyzed content

### 📚 Knowledge Library

- **Full-text + semantic search** across all analyses
- Filter by content type (articles, videos, repos)
- Topic-based organization
- Sort by recency or popularity

### 🌐 Multi-Source Support

- **Web articles** via Jina AI Reader
- **YouTube videos** with transcript extraction
- **GitHub repositories** with architecture analysis

---

## 🛠️ Tech Stack

### Backend
- **Framework:** FastAPI 0.121.2+
- **AI Orchestration:** LangGraph 1.0 + LangChain 1.0 (Sprint 2)
- **Database:** PostgreSQL 17 + PGVector 0.4.1
- **LLM:** Multi-provider support (Ollama for dev, GPT-5 Mini/Claude/Gemini for production)
- **Language:** Python 3.13

### Frontend
- **Framework:** React 19.0.0
- **Build Tool:** Vite 6.0.3
- **Styling:** Tailwind CSS 3.4.15
- **State Management:** TanStack Query 5.62.7 + Zustand 5.0.2
- **Language:** TypeScript 5.7.2

### Infrastructure
- **Containerization:** Docker Compose
- **Vector Search:** PGVector
- **Content Extraction:** Jina AI, YouTube Transcript API, PyGithub

---

## 🚀 Quick Start

### Prerequisites

- **Docker Desktop** (v24+)
- **Python** 3.13
- **Node.js** 20+
- **Git**

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/ArieGoldkin/SkillForge.git
cd SkillForge

# 2. Run setup script
chmod +x scripts/setup.sh
./scripts/setup.sh

# 3. Start backend
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
uvicorn app.main:app --reload

# 4. Start frontend (in new terminal)
cd frontend
npm run dev

# 5. Open browser
# Frontend: http://localhost:5173
# Backend API: http://localhost:8500/docs
```

### Environment Variables

**Backend (`.env`):**
```env
# Database
DATABASE_URL=postgresql://dev:devpass@localhost:5437/skillforge

# Multi-Provider LLM Configuration
LLM_MODEL=ollama:llama3.3:8b  # Development (free, local)
# LLM_MODEL=gpt-5-mini         # Production: GPT-5 Mini ($0.25/$2.00) - RECOMMENDED
# LLM_MODEL=claude-sonnet-4    # Anthropic Claude 4 Sonnet
# LLM_MODEL=gemini-2.0-flash   # Google Gemini 2.0 Flash

# Provider API Keys (set based on provider)
OPENAI_API_KEY=sk-...          # Required for OpenAI models (GPT-5 Mini, GPT-5, etc.)
# ANTHROPIC_API_KEY=sk-ant-...  # Required for Anthropic models (Claude)
# GOOGLE_API_KEY=...            # Required for Google models (Gemini)
# XAI_API_KEY=...               # Required for xAI models (Grok)
# DEEPSEEK_API_KEY=...          # Required for DeepSeek models

# Legacy Ollama (for embeddings / backwards compatibility)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.3:8b

# Content Extraction
JINA_API_KEY=your_key_here  # Get free key at https://jina.ai
```

**See `backend/.env.example` for complete configuration with verified November 2025 pricing.**

**Frontend (`.env.local`):**
```env
VITE_API_BASE_URL=http://localhost:8500
```

---

## 📚 Documentation

### For Developers

- **[User Stories](docs/USER_STORIES.md)** - Product requirements (16 user stories)
- **[Frontend Tasks](docs/ARIE_FRONTEND_TASKS.md)** - React 19 implementation guide
- **[Backend Tasks](docs/YONATAN_BACKEND_TASKS.md)** - FastAPI + LangGraph guide
- **[Integration Points](docs/INTEGRATION_POINTS.md)** - Coordination protocol
- **[Roadmap](docs/ROADMAP_PARALLEL.md)** - Parallel development roadmap

### For Users

1. **Submit a URL** for analysis (article, YouTube video, or GitHub repo)
2. **View real-time progress** as AI agents analyze the content
3. **Download the markdown artifact** with implementation guidance
4. **Optional:** Enter tutoring mode to learn concepts interactively
5. **Browse your library** of past analyses with search and filters

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                       FRONTEND                           │
│              React 19 + Vite (Vercel)                    │
│         ┌─────────────┬─────────────┬─────────────┐     │
│         │   Analyze   │   Tutor     │   Library   │     │
│         └─────────────┴─────────────┴─────────────┘     │
│                          ↕ (SSE + REST)                  │
└──────────────────────────────────────────────────────────┘
                             ↕
┌──────────────────────────────────────────────────────────┐
│                    BACKEND (Python)                      │
│                FastAPI + LangGraph                       │
│  ┌────────────────────────────────────────────────────┐ │
│  │         LangGraph Multi-Agent Workflow             │ │
│  │  Extract → Supervisor → 8 Agents → Aggregate      │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │       Content Extraction Services                  │ │
│  │  • Jina AI Reader  • YouTube API  • GitHub API    │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
                             ↕
┌──────────────────────────────────────────────────────────┐
│              PostgreSQL + PGVector                       │
│  • Analyses  • Artifacts  • Tutoring  • Embeddings     │
└──────────────────────────────────────────────────────────┘
```

---

## 🎯 Development Roadmap

### Phase 1: Foundation ✅ (Planning Complete)
- Backend scaffolding (FastAPI, PostgreSQL, Docker)
- Frontend scaffolding (React 19, Vite, Tailwind)
- Content extraction (Jina AI Reader)
- Basic analysis workflow

### Phase 2: Multi-Agent Pipeline (In Progress)
- LangGraph supervisor pattern
- 8 specialized sub-agents
- Artifact generation
- SSE progress streaming

### Phase 3: Tutoring System (Planned)
- Socratic dialogue engine
- Context-aware tutoring
- Session persistence

### Phase 4: Knowledge Library (Planned)
- Full-text + semantic search
- Topic extraction
- Filtering and sorting

### Phase 5: Content Expansion (Planned)
- YouTube video support
- GitHub repository analysis

### Phase 6: Production Launch (Planned)
- E2E testing
- Performance optimization
- Deployment (Vercel + backend hosting)

---

## 🤝 Contributing

We welcome contributions! This project follows a **parallel development workflow** with clear separation between frontend and backend tasks.

### Getting Started

1. Fork the repository
2. Read the [Integration Points](docs/INTEGRATION_POINTS.md) guide
3. Check [User Stories](docs/USER_STORIES.md) for available features
4. Pick a task from [Frontend Tasks](docs/ARIE_FRONTEND_TASKS.md) or [Backend Tasks](docs/YONATAN_BACKEND_TASKS.md)
5. Submit a pull request

### Git Workflow

**Branch Strategy:**
- **`main`** - Production-ready code (protected, requires PR)
- **`dev`** - Development branch (default for all PRs)
- **`feature/*`** - Feature branches for new work

**Pull Request Process:**
1. Create feature branch from `dev`: `git checkout -b feature/issue-X-description`
2. Make changes and commit
3. **Open PR targeting `dev` branch** (not `main`)
4. After review and approval, PR is merged into `dev`
5. `dev` is periodically merged into `main` for releases

**Important:** All new pull requests must target the `dev` branch.

### Development Workflow

- **Daily async standups** (15 min) - Update task status
- **Weekly integration checkpoints** (1 hour) - Demo and sync
- **API contract meetings** - Align on schemas before implementation
- **Pair programming** - For blocked tasks or complex integration

---

## 📊 Project Stats

- **Total Story Points:** 242 (105 frontend + 137 backend)
- **Sprints:** 7 (11-13 weeks)
- **User Stories:** 16 across 4 epics
- **Tech Stack:** React 19, FastAPI, LangGraph, PostgreSQL
- **Team:** 2 developers (frontend + backend)

---

## 🔒 Security

- **No secrets in repository** - Use `.env` files (excluded from git)
- **API keys required:** Jina AI (free tier available)
- **Database:** PostgreSQL with proper authentication
- **CORS:** Configured for local development

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **LangChain & LangGraph** for agent orchestration framework
- **Jina AI** for content extraction API
- **Anthropic Claude** for AI-powered analysis
- **React Team** for React 19 features
- **FastAPI** for modern Python web framework

---

## 📞 Contact

- **GitHub:** [@ArieGoldkin](https://github.com/ArieGoldkin)
- **Repository:** [SkillForge](https://github.com/ArieGoldkin/SkillForge)
- **Issues:** [Report a bug](https://github.com/ArieGoldkin/SkillForge/issues)

---

**Built with ❤️ using Claude Code**

*Last Updated: November 21, 2025*
