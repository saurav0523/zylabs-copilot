# ZyLabs AI Research Copilot

> A production-grade AI sales research assistant powered by LangGraph, FastAPI, React, Firecrawl, and PostgreSQL.

## 🎯 What it does

Given a company name, website, and a meeting objective, the copilot executes a deterministic, multi-agent AI pipeline to compile a comprehensive executive briefing.

1. **Plans** which pages to scrape using intelligent target selection.
2. **Crawls** the web in real-time using Firecrawl and Tavily (with smart in-memory caching).
3. **Extracts** structured business signals using highly constrained LLM parsing.
4. **Evaluates** its own output using an automated QA Check (with automatic LLM fallback and scraper retries).
5. **Generates** an 8-section structured markdown briefing.
6. **Streams** real-time execution progress to the browser via WebSockets.

The user can view the fully populated briefing UI and engage in an interactive follow-up chat with the AI contextually grounded in the report data.

## 🏗️ Architecture Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, TailwindCSS, Zustand, React Query |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.x (async), Alembic |
| AI Workflow | LangGraph (`StateGraph`), OpenRouter (Claude/Llama) |
| Web Research | Firecrawl API, Tavily API |
| App State / Data | PostgreSQL (Neon) |
| Cache / WS State | In-Memory (Dict) - Zero Config |
| Container | Docker + Docker Compose |

## Project Structure

```
zylabs-copilot/
├── frontend/
│   ├── src/
│   │   ├── components/        # SessionCreate, SessionList, WorkflowProgress, ChatPanel
│   │   ├── hooks/             # useWorkflowSocket, useSession, useChat
│   │   ├── store/             # Zustand slices
│   │   ├── api/               # React Query hooks over REST endpoints
│   │   └── types/             # Shared TypeScript interfaces
│   ├── package.json
│   └── vite.config.ts
├── backend/
│   ├── api/                   # FastAPI routers: sessions, workflow, chat, websocket
│   ├── workflow/
│   │   ├── graph.py           # StateGraph definition
│   │   ├── state.py           # GraphState TypedDict
│   │   └── nodes/             # planner, researcher, analyst, qa_check, reporter
│   ├── services/              # firecrawl.py, llm.py, websocket_manager.py
│   ├── db/                    # SQLAlchemy models, async session, Alembic migrations
│   ├── config.py              # Pydantic Settings
│   ├── main.py                # FastAPI app entry point
│   └── tests/                 # pytest test suite
├── docs/
│   ├── architecture.md
│   ├── engineering-decisions.md
│   ├── product-improvements.md
│   └── rules.md
├── docker-compose.yml
├── .env.example
└── README.md
```

## Quick Start

### Prerequisites
- Docker + Docker Compose
- Firecrawl API key ([firecrawl.dev](https://firecrawl.dev))
- OpenRouter API key ([openrouter.ai](https://openrouter.ai)) — free tier available

### Setup

```bash
git clone https://github.com/<you>/zylabs-copilot
cd zylabs-copilot

cp .env.example .env
# Edit .env and fill in your API keys

docker compose up --build
```

Frontend: http://localhost:5173  
Backend API: http://localhost:8000  
API docs: http://localhost:8000/docs

### Running without Docker

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Environment Variables

Copy `.env.example` and fill in values:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/zylabs
REDIS_URL=redis://localhost:6379/0

FIRECRAWL_API_KEY=fc-...
ANTHROPIC_API_KEY=sk-ant-...   # or OPENAI_API_KEY=sk-...

LOG_LEVEL=INFO
MAX_RETRY_COUNT=2
QA_QUALITY_THRESHOLD=0.7
MAX_PAGES_PER_SESSION=10
```

## Running Tests

```bash
cd backend
pytest --cov=. --cov-report=term-missing

cd frontend
npm run test
```

## Key Design Decisions

See [engineering-decisions.md](docs/engineering-decisions.md) for full rationale on:
- Why `StateGraph` over an agent loop
- Why WebSockets over SSE
- Why Firecrawl over Tavily / SerpAPI

## Architecture

See [architecture.md](docs/architecture.md) for the full system diagram, data flow, API contracts, and storage schema.

## Development Rules

See [rules.md](docs/rules.md) before writing any code. All rules are mandatory and enforced in CI.

## Product Thinking

See [product-improvements.md](docs/product-improvements.md) for identified weaknesses, prioritised improvements, success metrics, and the 90-day roadmap.

## API Reference (summary)

| Method | Path | Description |
|---|---|---|
| POST | `/api/sessions` | Create a new research session |
| GET | `/api/sessions` | List all sessions |
| GET | `/api/sessions/:id` | Get session + report |
| POST | `/api/sessions/:id/run` | Trigger LangGraph workflow |
| POST | `/api/sessions/:id/chat` | Follow-up chat on report |
| WS | `/ws/session/:id` | Real-time workflow progress stream |

## WebSocket Event Schema

```json
{
  "event": "node_started | node_done | workflow_complete | error",
  "node": "planner | researcher | analyst | qa_check | reporter",
  "timestamp": "2024-01-15T10:30:00Z",
  "payload": {}
}
```
