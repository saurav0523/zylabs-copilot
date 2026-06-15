# rules.md — Development Rules & Constraints

> These rules are **mandatory**. PRs that violate them will not be merged.
> Every rule has a "why" — understand it, don't just comply.

---

## 1. Architecture Compliance

**R-01 — Never skip a layer.**
Frontend must not call the LangGraph graph directly. Backend must not import React components. Each layer communicates only through the defined contracts in `architecture.md`. Violation = architectural coupling that makes the system impossible to test or replace.

**R-02 — No hardcoded configuration.**
Zero secrets, URLs, model names, thresholds, or timeouts in source code. Every tunable value lives in `config.py` and is loaded from environment variables. If you find yourself typing `"sk-..."` or `"postgresql://..."` in source, stop.

**R-03 — LangGraph graph shape is fixed in `workflow/graph.py`.**
The five-node pipeline (Planner → Researcher → Analyst → QA Check → Reporter) is the canonical shape. Do not add nodes, remove nodes, or rewire edges without updating `architecture.md` and `engineering-decisions.md` in the same PR. Adding a shortcut LLM call outside the graph is strictly prohibited.

**R-04 — All persistent state goes through the DB layer.**
Nodes must not write to PostgreSQL directly. State is carried in `GraphState` during execution, then persisted by the API layer after `workflow_complete`. Memory is for ephemeral coordination only (WebSocket registry, in-flight state snapshots, scrape cache).

---

## 2. No Deprecated Code

**R-05 — Use only current, maintained APIs.**
- Python 3.11+. No `asyncio.coroutine` decorator, no `yield from` coroutines.
- FastAPI 0.110+. No `@app.on_event("startup")` — use `lifespan` context manager.
- LangGraph: use `StateGraph` with `TypedDict` state, not the legacy `MessageGraph`.
- SQLAlchemy 2.x async API only. No `Session.execute()` with string SQL — use ORM or `select()` constructs.
- React 18+. No class components, no `componentDidMount`, no `React.FC` with `children` prop issues. Use functional components and hooks only.

**R-06 — No `any` in TypeScript.**
TypeScript strict mode is on. `any` is banned. Use proper types or `unknown` with type guards. The frontend `tsconfig.json` enforces this — do not loosen it.

**R-07 — No `print()` statements in production code.**
Use `structlog` in the backend. `console.log` is allowed only behind `if (import.meta.env.DEV)`. Every log must carry a `session_id` where applicable.

---

## 3. LangGraph-Specific Rules

**R-08 — Every node must emit a WebSocket event.**
Before a node returns its updated state, it must call `ws_manager.broadcast(session_id, event)`. Nodes that silently compute without telling the frontend are useless for the progress UI.

**R-09 — Nodes are pure functions of state.**
A node receives `GraphState`, returns updated `GraphState`. No global mutable variables inside node functions. No direct DB writes from inside nodes. This makes nodes testable in isolation.

**R-10 — All nodes must handle their own exceptions.**
Every node must have a `try/except` that catches exceptions, sets `state["error"]`, and returns the state so the graph can route to `fail_safe`. A node that raises an unhandled exception will crash the background task silently.

**R-11 — Retry count must be respected.**
The `qa_check` router must honour `state["retry_count"]`. Hard cap is `config.MAX_RETRY_COUNT` (default 2). Never route back to `researcher` if retry count is at or above the cap — this prevents infinite loops.

**R-12 — Graph state mutations are immutable-style.**
Never mutate a nested object in `GraphState` in-place. Return a new dict or use `{**state, "key": new_value}`. LangGraph's state reducers depend on this.

---

## 4. API Design Rules

**R-13 — All API responses follow the envelope pattern.**
Success: `{ data: <payload>, request_id: <uuid> }`
Error: `{ error: <message>, code: <string>, request_id: <uuid> }`
Never return a raw object at the top level and never return a raw Python traceback.

**R-14 — WebSocket messages follow the event schema.**
```json
{
  "event": "node_started" | "node_done" | "workflow_complete" | "error",
  "node": "<node_name>",
  "timestamp": "<ISO-8601>",
  "payload": {}
}
```
Do not invent new event shapes without updating the frontend `useWorkflowSocket` hook and this document.

**R-15 — HTTP status codes must be semantically correct.**
- `201` for resource creation, not `200`.
- `202` for async job acceptance (`/sessions/:id/run`), not `200`.
- `422` for validation errors (FastAPI default), not `400`.
- `503` if Firecrawl or the LLM provider is unreachable, not `500`.

---

## 5. Data & Security Rules

**R-16 — Validate all incoming data at the API boundary.**
Use Pydantic models for every request body and response. No `request.body()` raw parsing. No `dict["key"]` access on unvalidated input.

**R-17 — Sanitize company website input.**
The `website` field in `POST /sessions` must be validated as a proper URL (scheme + hostname). The Firecrawl integration must not be called with arbitrary user-supplied strings — always pass through the validated URL from the DB row.

**R-18 — Never log sensitive data.**
API keys, full scraped page content, and user objectives must not appear in logs at `INFO` or above. Use `DEBUG` level for raw payloads, and strip keys from debug logs in CI.

---

## 6. Testing Rules

**R-19 — Every LangGraph node must have a unit test.**
Node tests mock the LLM client and Firecrawl client. They test: happy path, exception path (sets `state["error"]`), and retry logic where applicable. Minimum coverage: 80% per node file.

**R-20 — API endpoints must have integration tests.**
Use `httpx.AsyncClient` with `TestClient`. Test: success path, missing session 404, invalid payload 422, and WebSocket event sequence.

**R-21 — Frontend components must have snapshot + interaction tests.**
Use Vitest + React Testing Library. `SessionCreate` form submission, `WorkflowProgress` rendering from mock WS events, `ChatPanel` send and receive.

---

## 7. Code Quality Rules

**R-22 — All Python files must pass `ruff` and `mypy --strict`.**
CI blocks merge on any lint or type error. Run `make lint` before pushing.

**R-23 — All TypeScript files must pass `eslint` with the project config.**
The eslint config enforces: no `any`, no unused imports, React hooks rules. Run `npm run lint` before pushing.

**R-24 — No file longer than 300 lines.**
If a file exceeds 300 lines, it is doing too much. Split it. This is a hard limit, not a guideline.

**R-25 — Imports must be organised.**
Python: stdlib → third-party → local (enforced by `ruff`).
TypeScript: external packages → internal `@/` paths → relative paths.

---

## 8. Git & PR Rules

**R-26 — Branch naming: `feature/<name>`, `fix/<name>`, `chore/<name>`.**
No work on `main` directly. All changes via PR.

**R-27 — Commit messages follow Conventional Commits.**
`feat:`, `fix:`, `chore:`, `docs:`, `test:`. No `"misc"`, `"stuff"`, or `"WIP"` as full commit messages.

**R-28 — PRs that touch `workflow/graph.py` must update `architecture.md`.**
The architecture document is the source of truth for the graph shape. If the code and the doc diverge, the doc is wrong — fix it.

**R-29 — Every PR must include a test.**
No code PR without at least one new or updated test. Documentation-only PRs are exempt.

---

## Quick Reference Checklist

Before opening a PR, verify:

- [ ] No hardcoded secrets or config values
- [ ] No deprecated APIs (see R-05)
- [ ] All nodes emit WebSocket events (R-08)
- [ ] All nodes handle exceptions (R-10)
- [ ] API responses follow envelope pattern (R-13)
- [ ] `ruff`, `mypy`, and `eslint` pass with zero errors
- [ ] At least one new test added
- [ ] If graph shape changed → `architecture.md` updated
