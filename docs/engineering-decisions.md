# engineering-decisions.md

## Decision 1 — LangGraph `StateGraph` with `TypedDict` over agent-loop patterns

**Context:** The workflow requires multiple steps (planning, scraping, analysis, QA, report generation) with conditional routing (retry on low quality). Two approaches were viable: a simple agent loop (LLM decides what tool to call next) or an explicit `StateGraph` with defined nodes and edges.

**Decision:** Use `StateGraph` with a fixed topology and explicit conditional routing via `add_conditional_edges`.

**Alternatives considered:**
- **ReAct agent loop:** LLM autonomously decides next steps. Rejected because it gives the LLM too much autonomy over workflow topology — the QA retry logic and the structured 8-section report require deterministic control flow, not emergent tool selection.
- **Simple sequential chain:** No conditional routing, no retry. Rejected because QA-driven retry was a hard requirement.

**Tradeoffs:**
- Explicit graph = more code upfront, but fully observable, debuggable, and testable per-node.
- The graph topology is visible in `workflow/graph.py` — new engineers can understand the full flow in minutes.
- Downside: adding a new research step requires wiring a new node and edge; agent loops are more flexible for ad-hoc tool use.

---

## Decision 2 — WebSockets over SSE for workflow progress streaming

**Context:** Workflow execution takes 30–90 seconds. Users need real-time node-by-node progress updates.

**Decision:** Use WebSockets (`wss://`) managed by `websocket_manager.py`, with connection state stored in Memory.

**Alternatives considered:**
- **Server-Sent Events (SSE):** Simpler — unidirectional, HTTP/1.1 compatible, automatic reconnect. Rejected because the follow-up chat feature already requires bidirectional communication. Having one WebSocket per session covers both progress and future chat extensions cleanly.
- **HTTP polling (every 2s):** Simplest implementation. Rejected — 30+ second workflows = 15+ redundant poll requests per session; poor UX, wastes compute.

**Tradeoffs:**
- WebSockets require managing connection lifecycle (open, ping/pong, close, reconnect on client drop).
- Memory is required to store which connections are active and to fan out events from the background task to the socket handler — adds operational complexity.
- Upside: instant feedback (< 100ms latency on node transitions), single persistent connection, extensible to real-time collaborative features later.

---

## Decision 3 — Firecrawl for web research over Tavily / SerpAPI

**Context:** The Researcher node needs to gather information from company websites and public web pages.

**Decision:** Use Firecrawl's `/scrape` and `/crawl` endpoints to get clean Markdown content from URLs.

**Alternatives considered:**
- **Tavily Search API:** Returns search results with snippets, not full page content. Better for broad discovery, worse for deep per-page extraction. Rejected because the Planner node already narrows targets to specific URLs; we need full content, not snippets.
- **SerpAPI:** Returns Google search results. Same issue as Tavily — snippets, not full content. Also more expensive per query.
- **Direct `httpx` + `BeautifulSoup`:** Free, no API key needed. Rejected — Firecrawl handles JS-rendered pages, bot-detection avoidance, and Markdown conversion out of the box. Building this ourselves would take more time than the assignment allows.

**Tradeoffs:**
- Firecrawl adds an external API dependency and cost per scrape.
- Mitigated by a 24-hour Memory cache on `scrape:cache:<url_hash>` — repeated runs on the same company don't re-scrape.
- Risk: Firecrawl rate limits could throttle the Researcher node on large crawls; mitigated by `MAX_PAGES_PER_SESSION` config value (default: 10).

---

## Decision 4 — Recoverability Design & Failure Mitigation (Assignment Compliance)

**Context:** AI agent pipelines are inherently prone to transient issues (network timeouts, LLM output formatting errors, website scrapers blocking access). We need a clear, mature recovery strategy instead of failing catastrophically.

**Decision:** Implement a multi-tiered recovery and best-effort delivery architecture:
1. **Scraper Retry & Cache:** `firecrawl_service` uses exponential backoff (3 attempts, max 30s) and writes results to a 24-hour Memory cache. If a URL scraping attempt fails but later retries, it uses the cached response, reducing external network hits.
2. **LLM Output Fallback:** `llm_service.generate_json` wraps LLM prompts. If parsing fails, it retries with a fallback prompt requesting simple, raw JSON formatting without markdown blocks.
3. **Graph Level try/except:** If a node raises an exception, the node catches it, sets `state["error"] = ...`, and returns the state. The graph topology continues to run and ultimately triggers the `reporter` node to build a best-effort compilation using whatever data is present.
4. **Best-Effort Saving:** The FastAPI task runner commits reports to the database even if the session ended with errors (`FAILED`), ensuring the user retains access to partial findings.
5. **Manual Retry Action:** The frontend displays partial reports with warning indicators and offers a "Retry Workflow" option to clear logs and re-trigger execution.

**Tradeoffs:**
- Preserving partial/best-effort reports means a session status can be `FAILED` but still have a report relation. This requires the frontend to handle partial views, increasing code complexity slightly, but greatly improving UX by avoiding "all-or-nothing" execution failures.

---

## Top Technical Debt Items

**TD-01 — Background tasks run in-process (FastAPI `BackgroundTasks`).**
For the MVP this is fine, but long-running workflows (> 60s) may time out under load. The proper fix is a dedicated task queue (Celery + Memory or ARQ). Migration path is clean — the `workflow/graph.py` and `websocket_manager.py` are already decoupled from the HTTP request lifecycle.

**TD-02 — No LangGraph checkpointing.**
LangGraph supports `MemorySaver` and `PostgresSaver` checkpointers for mid-graph state persistence and resumability. Currently, if the server restarts mid-workflow, the session is stuck in `running` status. Fix: integrate `PostgresSaver` using the existing DB connection.

**TD-03 — Chat context is the full report JSON.**
The follow-up chat sends the entire report as context to the LLM. For large reports this wastes tokens. Should be replaced with a retrieval step (embed report sections, retrieve top-k relevant sections per question).

**TD-04 — No rate limiting on the API.**
`POST /sessions/:id/run` can be called multiple times in parallel per session. Should add Memory-backed rate limiting per IP and per session.

**TD-05 — Frontend has no offline / reconnect handling.**
If the WebSocket drops mid-workflow, the progress UI freezes. Should implement auto-reconnect with exponential backoff and re-fetch current workflow state on reconnect.

---

## Biggest Technical Risk

**Firecrawl reliability under adversarial inputs.** If a user submits a company website that blocks scrapers, returns a login wall, or redirects to a CAPTCHA, the Researcher node will receive empty or near-empty content. The downstream LLM steps will produce low-quality analysis, the QA check will trigger retries, and after 2 retries the reporter will generate a best-effort (but visibly thin) report. 

Mitigation: the Planner node is prompted to identify multiple alternative URLs (LinkedIn, Crunchbase, news articles) beyond just the company's homepage. This diversifies scrape sources so a blocked homepage doesn't sink the whole workflow.

---

## What I Would Improve with 2 Additional Weeks

1. **LangGraph checkpointing with `PostgresSaver`** — makes workflows resumable after server restart; critical for production reliability.
2. **Celery task queue** — move workflow execution off the FastAPI process; enables horizontal scaling and proper retry/dead-letter handling.
3. **RAG-based chat context** — embed report sections into pgvector, retrieve top-k per user question; reduces token cost by 70%+ on long reports.
4. **Streaming LLM output** — pipe LLM token stream directly through the WebSocket to the frontend during the Reporter node; dramatically improves perceived latency.
5. **Role-based session sharing** — allow multiple users to view the same session's report (read-only link); essential for the "send a briefing to a colleague" use case.
