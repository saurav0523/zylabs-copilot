# Architecture — ZyLabs AI Research Copilot

## Overview

The system is a full-stack AI application with four distinct layers: a React frontend, a FastAPI backend, a LangGraph AI workflow engine, and a PostgreSQL + Redis persistence layer. All layers communicate through well-defined contracts; no layer reaches across another.

```
Browser (React + Vite)
    │  REST (HTTPS)       WebSocket (WSS)
    ▼                          ▼
FastAPI (Python)  ─────────────────────
    │  Session / Workflow / Chat APIs
    ▼
LangGraph Workflow Engine
    │  Firecrawl API (external)
    ▼
PostgreSQL  │  Redis  │  Local file cache
```

---

## Layer Breakdown

### 1. Frontend — React + Vite + TypeScript

**Responsibility:** Render UI, manage local state, open one persistent WebSocket per active research session.

**Key components:**

| Component | Route | Purpose |
|---|---|---|
| `SessionCreate` | `/` | Company name, website, research objective form |
| `SessionList` | `/sessions` | Paginated history of past sessions |
| `SessionDetail` | `/sessions/:id` | Report viewer + follow-up chat |
| `WorkflowProgress` | embedded in detail | Live LangGraph node status via WebSocket |
| `ChatPanel` | embedded in detail | Follow-up Q&A, sends to `/api/chat` |

**State management:** Zustand for global session state; React Query for server-cache sync.

**WebSocket flow:**
1. On session start, open `wss://<host>/ws/session/<session_id>`.
2. Backend emits `{ event: "node_started" | "node_done" | "workflow_complete" | "error", node, payload }`.
3. Frontend renders a step-by-step progress UI from these events.
4. Socket closes automatically on `workflow_complete` or `error`.

---

### 2. Backend — Python + FastAPI

**Responsibility:** Expose REST and WebSocket endpoints, orchestrate LangGraph execution in a background task, persist all state.

**Module structure:**

```
backend/
├── main.py                  # FastAPI app, CORS, router registration
├── api/
│   ├── sessions.py          # POST /sessions, GET /sessions, GET /sessions/:id
│   ├── workflow.py          # POST /sessions/:id/run  (triggers BG task)
│   ├── chat.py              # POST /sessions/:id/chat
│   └── websocket.py         # WS /ws/session/:id
├── workflow/
│   ├── graph.py             # LangGraph StateGraph definition
│   ├── nodes/
│   │   ├── planner.py
│   │   ├── researcher.py
│   │   ├── analyst.py
│   │   ├── qa_check.py
│   │   └── reporter.py
│   └── state.py             # Typed GraphState TypedDict
├── services/
│   ├── firecrawl.py         # Firecrawl API client wrapper
│   ├── llm.py               # Anthropic / OpenAI client factory
│   └── websocket_manager.py # Connection registry, broadcast helpers
├── db/
│   ├── models.py            # SQLAlchemy ORM models
│   ├── session.py           # Async engine + session factory
│   └── migrations/          # Alembic migration scripts
├── config.py                # Pydantic Settings from env
└── logging_config.py        # Structured JSON logging
```

**API contracts:**

```
POST   /api/sessions                → { id, status, created_at }
GET    /api/sessions                → [ session... ]
GET    /api/sessions/:id            → session + report (if done)
POST   /api/sessions/:id/run        → { status: "queued" }
POST   /api/sessions/:id/chat       → { reply, sources }
WS     /ws/session/:id              → stream of WorkflowEvent JSON
```

### 3. LangGraph Workflow

**Responsibility:** Orchestrate the multi-step AI research pipeline with shared state, conditional routing, and failure recovery.

#### Topology Selection & Rationale
We selected a structured **Directed Acyclic Graph (DAG) with an explicit feedback loop** rather than a free-agent loop (where the LLM determines tool executions dynamically). This decision ensures:
1. **Deterministic Execution Stages:** Sales intelligence discovery requires sequential steps (plan -> scrape -> extract -> QA -> report) to keep the pipeline observable and predictable.
2. **Quality Enforcement:** The QA audit step acts as a gateskeeper checking compliance against `QA_QUALITY_THRESHOLD` (0.7).
3. **Guardrails against infinite loops:** The state tracks `retry_count`, stopping after 2 retries and forcing a best-effort report compilation.

#### Graph State (`state.py`)
```python
class GraphState(TypedDict):
    session_id: str                  # Unique session tracking ID
    company_name: str                # Target company name
    website: str                     # Initial domain seed URL
    objective: str                   # Sales meeting target objective
    scrape_targets: List[str]       # Target URLs compiled by Planner
    scraped_pages: List[dict]       # Markdown content ingested by Researcher
    research_notes: str             # Synthesized raw text passing to Analyst
    analysis: dict                  # Structured signals parsed by Analyst
    quality_score: float            # Audit rating score (0.0 to 1.0)
    retry_count: int                # Feedback loops completed (Max: 2)
    report: dict | None             # Final 8-section briefing
    error: str | None               # Error details if a node fails
```

#### Shared State Evolution
During execution, the state evolves sequentially:
1. **Planner Input:** (`company_name`, `website`, `objective`) -> **Output:** Adds `scrape_targets`.
2. **Researcher Input:** (`scrape_targets`) -> **Output:** Adds `scraped_pages` (list of raw markdown strings) and `research_notes` (concatenated string of markdown contents).
3. **Analyst Input:** (`research_notes`) -> **Output:** Adds `analysis` (structured business JSON keys).
4. **QA Check Input:** (`analysis`) -> **Output:** Adds `quality_score` (float rating). If the score is `< 0.7` and `retry_count < 2`, increments `retry_count`.
5. **Reporter Input:** (`analysis`) -> **Output:** Adds `report` (structured 8-section markdown briefing).

#### Nodes

| Node | Input | Output | External Calls & Integration |
|---|---|---|---|
| `planner` | company_name, website, objective | scrape_targets | LLM (claude-3-5-sonnet-20240620 / gpt-4o) |
| `researcher` | scrape_targets, retry_count | scraped_pages, research_notes | Firecrawl `/scrape` and `/crawl` APIs |
| `analyst` | research_notes | analysis | LLM (claude-3-5-sonnet-20240620 / gpt-4o) |
| `qa_check` | analysis | quality_score, retry_count | LLM (claude-3-5-sonnet-20240620 / gpt-4o) |
| `reporter` | analysis | report | LLM (claude-3-5-sonnet-20240620 / gpt-4o) |

#### Graph Definition
```
planner → researcher → analyst → qa_check
                                    │
                 quality ≥ 0.7 ──── ┼ ──── reporter
                 quality < 0.7      │
                 retry_count < 2 ── ┘ → researcher (retry with wider crawl)
                 retry_count ≥ 2 ──────→ reporter (best-effort compilation)
```

#### Conditional Routing Decision Matrix
The routing edge function `route_after_qa` evaluates state keys:
- **Error shortcut:** If `state["error"]` is set (meaning a failure occurred in previous nodes), it routes immediately to `reporter` to build a best-effort compilation using whatever data is available.
- **Pass path:** If `state["quality_score"] >= 0.7`, it routes to `reporter` for final formatting.
- **Retry loop:** If `state["quality_score"] < 0.7` and `state["retry_count"] < 2`, it routes back to `researcher` and triggers a wider crawl on the base domain.
- **Max retry path:** If `state["retry_count"] >= 2`, it routes to `reporter` to output whatever was collected.

#### Node-Level Exception Handling & Recoverability
1. **Try-Except Wrapper:** Every node function wraps execution in a `try/except` block. On catch:
   - Sets `state["error"] = "Node failed: [error message]"`.
   - Broadcasts an `"error"` WebSocket event to notifying the user.
   - Returns the state gracefully so downstream nodes (specifically `reporter`) can still run and compile a briefing document.
2. **Scraper Recovery (Firecrawl):** Includes custom exponential backoff (3 attempts starting at 2.0s delay, capped at 30s timeout) and caches all results in Redis (`scrape:cache:<url_hash>`) with a 24-hour TTL, avoiding repeated scraping on retries.
3. **Structured Output Recovery (LLM):** Uses `llm_service.generate_json` with fallback prompts. If structured extraction fails, it retries with a simplified prompt asking for raw JSON formatting.
4. **Best-Effort Saving:** If the pipeline finishes with errors, the FastAPI task runner checks if a report was compiled. If a report is present, it is saved to the database. The frontend displays this report with a warning and a "Retry Workflow" button to re-trigger execution.

#### WebSocket Progress Transmission
Nodes send updates using `ws_manager.broadcast`:
- `node_started`: Sent on entering node (displays spinner).
- `node_progress`: Sent during node execution with detailed logs (e.g., *"Scraping https://acme.org - 'About Us'"*), which render in the Live Activity Log.
- `node_done`: Sent on node completion (sets checkmark).
- `error`: Sent on node failures (updates warning panels).

### 4. Storage

#### PostgreSQL (primary store)

```sql
-- sessions
id            UUID PK
company_name  TEXT NOT NULL
website       TEXT NOT NULL
objective     TEXT NOT NULL
status        ENUM('pending','running','done','failed')
created_at    TIMESTAMPTZ DEFAULT now()
updated_at    TIMESTAMPTZ

-- reports
id            UUID PK
session_id    UUID FK → sessions.id
content       JSONB        -- full 8-section structured report
sources       JSONB        -- list of URLs used
quality_score FLOAT
created_at    TIMESTAMPTZ

-- chat_messages
id            UUID PK
session_id    UUID FK → sessions.id
role          ENUM('user','assistant')
content       TEXT
created_at    TIMESTAMPTZ
```

#### Redis

| Key pattern | TTL | Purpose |
|---|---|---|
| `ws:session:<id>:connections` | session lifetime | Active WebSocket connection registry |
| `workflow:state:<session_id>` | 1 hour | In-progress LangGraph state snapshot |
| `scrape:cache:<url_hash>` | 24 hours | Firecrawl response cache (avoid re-scraping) |

---

## Cross-Cutting Concerns

### Configuration (`config.py`)
All secrets and tunable values come from environment variables via Pydantic `Settings`. No hardcoded values anywhere. `.env.example` ships with the repo.

```
DATABASE_URL
REDIS_URL
FIRECRAWL_API_KEY
OPENAI_API_KEY (or ANTHROPIC_API_KEY)
LOG_LEVEL
MAX_RETRY_COUNT
QA_QUALITY_THRESHOLD
```

### Logging
Structured JSON logs via `structlog`. Every log entry carries `session_id`, `node`, `duration_ms`. Frontend errors are caught in an ErrorBoundary and logged to console (extend to Sentry in production).

### Error handling
- FastAPI exception handlers return `{ error, code, request_id }` — never raw tracebacks.
- LangGraph node errors set `state["error"]` and route to `fail_safe`.
- WebSocket disconnects are handled gracefully; the workflow continues and results are persisted regardless.

### Responsive design
Frontend uses Tailwind CSS. Breakpoints: mobile (< 768px) collapses the sidebar; tablet (768–1024px) single-column; desktop (> 1024px) split-pane (session list + detail).

---

## Data Flow — End to End

```
1. User fills form → POST /api/sessions           → DB: session row (status=pending)
2. User clicks Run → POST /api/sessions/:id/run   → BG task queued, status=running
3. WS /ws/session/:id opens                       → client listens for events

4. BG Task:
   planner    → emits { event:"node_started", node:"planner" }
              → emits { event:"node_done",    node:"planner", targets:[...] }
   researcher → Firecrawl scrapes URLs (cached in Redis)
              → emits node_started / node_done
   analyst    → LLM extracts structured signals
   qa_check   → LLM scores quality → conditional route
   reporter   → LLM generates final 8-section report
              → DB: report row saved
              → emits { event:"workflow_complete", report_id }

5. Frontend receives workflow_complete → fetches GET /api/sessions/:id → renders report
6. User sends follow-up → POST /api/sessions/:id/chat → LLM with report as context → reply
```
