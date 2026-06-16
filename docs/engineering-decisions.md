# Engineering Decisions

## Decision 1 — LangGraph StateGraph with explicit topology instead of an agent loop

When I started designing the workflow, the obvious first instinct was a ReAct-style agent where the LLM decides what tool to call next. It's the default pattern and it works fine for open-ended tasks. But this isn't an open-ended task — it's a fixed pipeline: plan, scrape, analyze, check quality, generate report. Every run should follow the same steps in the same order.

The problem with a free agent loop here is that the LLM might decide to skip the QA step on some runs, or call the scraper twice because it "felt" like it needed more data. That's unpredictable and untestable. I wanted to be able to look at `graph.py` and tell you exactly what will happen for any given input.

So I went with `StateGraph` and wired the nodes explicitly. The topology is the contract. If something breaks, I know exactly which node broke and what state it received. New engineers can read the graph definition in 5 minutes and understand the full flow.

The downside is it's more rigid — if I want to add a new research step later, I have to wire a new node and edge manually rather than just giving the agent a new tool. That's a fair tradeoff for a pipeline that has deterministic requirements.

**Alternatives I considered:**
- ReAct agent loop — rejected, too much LLM autonomy over something that needs to be predictable
- Simple LangChain sequential chain — rejected, no conditional routing, no retry loop

## Decision 2 — WebSockets over SSE for streaming workflow progress

The workflow takes 30-90 seconds to run. Showing a blank loading spinner for that long is terrible UX. Users need to see something happening — which node is running, what it found, when it's done.

I looked at three options: WebSockets, Server-Sent Events (SSE), and polling.

SSE was honestly tempting. It's simpler, unidirectional, and browsers handle reconnects automatically. But there's a catch — the follow-up chat feature also needs real-time communication, and SSE is one-directional only. I didn't want to run two separate real-time systems (SSE for workflow events, WebSocket for chat). One WebSocket per session handles both cleanly.

Polling every 2 seconds sounds fine until you realize a 60-second workflow means 30 HTTP requests per session, most of which return "still running." That's wasteful and the UX latency feels bad compared to pushed events.

WebSocket won. The tradeoff is I had to write connection lifecycle management — the `WebSocketManager` class handles connect, disconnect, broadcast, and dead-connection cleanup. That's maybe 80 lines of code for a noticeably better user experience.

**One thing I'd fix later:** The current WebSocket state lives in-process (Python dict). If the app ever scales to multiple processes, events from one worker won't reach connections on another. The fix is Redis pub/sub fan-out, but for a single-process MVP this isn't a real problem yet.

## Decision 3 — Firecrawl for web scraping instead of raw HTTP + BeautifulSoup

The Researcher node needs actual page content — not search snippets, not summaries, actual text. I need to hit a company's About page, their blog, their LinkedIn, and pull clean readable text out of it.

The DIY option (httpx + BeautifulSoup) is free and I control everything. But I've been down that road before — JS-rendered pages come back empty, bot detection blocks you, you spend 2 days debugging scraping edge cases instead of building the product. For a 3-day assignment that's not a good use of time.

Tavily was the other real option. It's good for search — returns snippets from multiple sources fast. But snippets aren't what I need. The Planner already figures out which specific URLs to target. I need full page content from those URLs, not a search result summary. That's what Firecrawl does well.

The main risk with Firecrawl is external dependency — if they're down, the Researcher node fails. I mitigated this with a 24-hour in-memory cache keyed by URL hash, so repeated runs on the same company (e.g., while testing) don't hit Firecrawl at all.

**What I'd do with more time:** Add a fallback scraper. If Firecrawl fails for a URL, try a direct httpx fetch and strip HTML with BeautifulSoup. It won't handle JS-heavy pages, but it's better than returning nothing.

## Decision 4 — In-process FastAPI BackgroundTasks instead of a proper task queue

This was the pragmatic call I'm least proud of but most comfortable defending for an MVP.

The workflow runs for 30-90 seconds. FastAPI's `BackgroundTasks` runs it in the same process after the HTTP response is sent. This works fine for low concurrency — the task completes, the DB gets updated, done.

The production-correct answer is Celery + Redis or ARQ — a separate worker process that picks up jobs from a queue, retries failed jobs, and doesn't tie up web server threads. That's the right architecture and it's in the tech debt list.

But setting up Celery for a 3-day assignment felt like over-engineering the infrastructure at the expense of the actual product features. The code is already structured so `_run_workflow()` is a standalone async function with no FastAPI dependencies — swapping it to a Celery task later is a clean migration, not a rewrite.

## Top Technical Debt Items

**TD-01 — In-process background tasks.** Works fine now, breaks under load. Celery migration when needed — the workflow function is already decoupled.

**TD-02 — No LangGraph checkpointing.** If the server restarts mid-workflow, that session is stuck at `running` forever. `MemorySaver` or `PostgresSaver` would fix this. One-line change to `graph.compile()`, I just didn't prioritize it.

**TD-03 — Chat sends the entire report as context.** For a 10-section report this is fine. For longer reports it wastes tokens and hits context limits. The right fix is embedding report sections into pgvector and retrieving the relevant chunk per user question — but that's a separate feature, not an MVP requirement.

**TD-04 — No per-session rate limiting on `/run`.** A user could spam the workflow endpoint. Should add a Redis-backed check: one active workflow per session at a time.

**TD-05 — WebSocket state is in-process.** Covered in Decision 2 above. Single process is fine for now.

## Biggest Technical Risk

Firecrawl returning empty or garbage content for the target company's website. This happens more than you'd expect — paywalls, login walls, JS-heavy SPAs that take 5 seconds to render, bot detection that returns a 403. When this happens, the Researcher node gets blank markdown, the Analyst has nothing to work with, the QA score tanks, and the retries also return blank content.

The Planner node helps here — it's prompted to generate 6-8 diverse URLs (not just the homepage) so one blocked URL doesn't sink the whole run. But if the company has heavy bot protection across their entire domain, the report will be thin regardless.

Longer-term mitigation: hybrid approach combining Firecrawl (full-page content) with Tavily (search-based discovery) so there's always a fallback content path.

## What I'd Improve with 2 More Weeks

1. **LangGraph checkpointing with `PostgresSaver`** — workflows become resumable after server restart, which is the "recoverability" requirement done properly rather than just graceful degradation.

2. **Move to Celery task queue** — proper worker separation, dead-letter queues, retry policies with backoff. This is the single biggest production-readiness gap.

3. **RAG for chat** — embed report sections, retrieve top-k per question instead of dumping the whole report into context. Saves tokens, handles longer reports, gives more accurate answers.

4. **Streaming LLM output to the browser** — currently the Reporter node blocks until the full report is generated. Piping tokens through the WebSocket would make it feel much faster.

5. **Section-level refresh** — let users re-run just "Business Signals" without redoing the full workflow. The LangGraph subgraph API supports this cleanly.
