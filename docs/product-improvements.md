# product-improvements.md

## 1. Five Weaknesses in the Current Product Design

**W-1 — Single-run, static reports.** Once a report is generated, it is frozen. The world changes — a company closes a funding round, loses a key executive, or launches a new product the day after the report was made. There is no way to refresh a stale section without re-running the full workflow.

**W-2 — No user context for the meeting.** The research objective is a freeform text field. The system has no idea whether the user is selling to a Series-A SaaS startup or negotiating a partnership with a Fortune 500. Without structured buyer/seller context, the "Suggested Outreach Strategy" and "Discovery Questions" are generic and low-value.

**W-3 — Report is a monolith, not a workspace.** The current design dumps an 8-section report on the user. There is no way to highlight a section, add a personal note, mark a signal as "already knew this", or collapse sections irrelevant to a specific meeting. It is a read-only document, not a tool.

**W-4 — No CRM or calendar integration.** Sales reps already have a workflow: Salesforce for contacts, Google Calendar for meetings, Slack for team communication. The copilot exists in isolation. Every insight the user gets must be manually copied out, which is the exact friction AI is supposed to eliminate.

**W-5 — Follow-up chat has no memory across sessions.** If a user researches Acme Corp today and again in 3 months, the second session starts completely fresh. There is no longitudinal intelligence — no "last time you researched this company, you noted X" — which would be highly valuable for account management.

---

## 2. Top 3 Improvements to Build Next

### Priority 1 — Structured buyer/seller context (solves W-2)

Before the workflow runs, ask the user 3–5 targeted questions:
- What is your role? (AE, SDR, founder, partnership lead)
- What is the meeting type? (first call, demo, negotiation, renewal)
- What does your product/service do? (one-line description)

This context is injected into the Planner and Reporter prompts. The output shifts from "here is everything about this company" to "here is what matters for *your* specific meeting". This is the single highest-leverage improvement — it makes every section of the report immediately actionable rather than informational.

### Priority 2 — Section-level refresh (solves W-1)

Allow users to re-run individual sections rather than the full workflow. A "Refresh Business Signals" button re-runs only the Researcher and Analyst nodes for that section, using the current date as a filter prompt. This is a LangGraph subgraph invocation — the architecture already supports it. Users keep their annotated report but get fresh data where it matters.

### Priority 3 — One-click CRM push (solves W-4)

Add a "Push to Salesforce / HubSpot" button on the report page. Map report sections to CRM fields: Company Overview → Account Description, Business Signals → Activity Notes, Discovery Questions → Next Steps task. This turns the copilot from a standalone research tool into a force-multiplier for an existing sales workflow, which is where the retention argument lives.

---

## 3. Who Buys It, Who Uses It, Why They Pay

**Buyer:** VP of Sales or Head of Revenue at a B2B SaaS company with a 10–200 person sales team. They care about rep productivity metrics — meetings booked per week, pipeline generated per rep, deal velocity. They buy tools that move those numbers.

**User:** Account Executives and SDRs who spend 20–40 minutes manually researching a company before every important call. They hate this task and do it inconsistently. Half of them skip it entirely when the calendar is full.

**Why they pay:** The copilot reduces pre-call research from 30 minutes to 3 minutes, per rep, per meeting. A team of 10 AEs doing 5 meetings/week saves 25 hours/week of research time. At a fully-loaded rep cost of $80–120/hour, that is $2,000–3,000/week in recovered time — far more than a $200–500/month SaaS subscription. The ROI argument is immediate and measurable.

---

## 4. Success Metrics

**Adoption:** Sessions created per user per week (target: ≥ 3 after onboarding). Active users / total registered users (DAU/MAU ratio, target: > 30%).

**Quality:** User rating on generated reports (thumbs up/down, target: > 80% positive). Average quality score from the QA check node (target: > 0.75).

**Business impact:** Self-reported time saved per session (collected via post-session survey, target: > 20 minutes saved). Pipeline influenced by accounts where the copilot was used (CRM integration metric, long-term).

**Reliability:** Workflow completion rate (successful `workflow_complete` / total runs, target: > 95%). P95 workflow duration (target: < 60s).

---

## 5. Four-Week AI Roadmap

| Week | Focus | Outcome |
|---|---|---|
| 1 | Structured context intake + prompt personalization | Reports are role-specific and meeting-type-specific |
| 2 | Section-level refresh + LangGraph subgraph invocation | Users can refresh stale sections without re-running everything |
| 3 | CRM push (Salesforce + HubSpot MVP via OAuth) | One-click export of report to CRM activity notes |
| 4 | Longitudinal account memory (pgvector embeddings of past reports) | "Last time" context injected into follow-up sessions on the same company |

---

## 6. Biggest Cost, Scaling, and Reliability Risks

**Cost:** LLM API costs scale linearly with sessions. The Reporter node sends ~10,000–20,000 tokens per run (scraped content + analysis + report generation). At $15/M tokens, 10,000 sessions/month = $1,500–3,000/month in LLM costs alone, before Firecrawl costs. Mitigation: cache Firecrawl responses aggressively; add a "lite mode" that skips deep crawl and uses only the company homepage.

**Scaling:** The current in-process BackgroundTask approach works for < 100 concurrent sessions. Above that, long-running workflows will exhaust FastAPI worker threads. Mitigation path: move to Celery + Redis task queue (already planned as TD-01 in `engineering-decisions.md`).

**Reliability:** The system has three external dependencies that can fail independently: Firecrawl, the LLM provider, and PostgreSQL. A Firecrawl outage silently produces empty research notes; an LLM outage kills the Analysis and Reporter nodes. Mitigation: circuit breakers on both external clients, graceful degradation (partial reports with "unavailable" placeholders), and a status page that reflects real-time dependency health.

---

## 7. Feature to Remove

**Remove:** The freeform research objective text field in its current form.

**Why:** Users write objectives like "prepare for sales call" — which is uselessly vague — or write a paragraph of context that the LLM partially ignores because the prompt doesn't structure it. The field adds a false sense of personalization without delivering it.

**Replace with:** Structured dropdowns (meeting type, user role) plus a short "additional context" optional field capped at 280 characters. This gives the LLM clean, structured input and takes the cognitive load off the user.

---

## 8. Feature to Add

**Add:** A "Red Flags" section to the report — automatically surfaced risk signals that are relevant to the user's role.

**Why:** Sales reps are incentivized to be optimistic. They often ignore signals that a prospect is a bad fit: high churn signals, legal troubles, leadership instability, recent funding cuts. A dedicated "Risks & Red Flags" section that the AI surfaces proactively changes the tool from a cheerleader into a genuine advisor. It also differentiates the product — most research tools surface positives. This one surfaces what not to miss.

---

## 9. First 90-Day Roadmap

**Days 1–30 (Prove the core):** Ship the MVP. Onboard 20 design-partner reps from 5 companies. Run weekly interviews. Instrument every session with logging (time spent on report, sections clicked, follow-up chat volume). Identify which report sections users actually read vs skip.

**Days 31–60 (Tighten the loop):** Ship structured context intake (Priority 1). Kill the report sections that usage data shows are universally ignored. Optimize P95 workflow duration to < 45s. Add thumbs up/down rating on the report page. Target: > 75% of design partners using the tool weekly without being prompted.

**Days 61–90 (Expand the value chain):** Ship CRM push (Priority 3). Begin Salesforce AppExchange listing process. Add a team dashboard for managers (sessions run, reports generated, average quality score). Start the sales motion: convert design partners to paid accounts. Target: 3 paid teams by Day 90.

---

## 10. What I Would Change First and Why

**I would add structured buyer/seller context intake before anything else.**

The biggest reason a research tool fails to become a habit is that the output isn't relevant enough to be trusted. A generic company overview is something a rep could get from the company's own website. The moment the report says "Given that you're an AE trying to book a first demo with the Head of Engineering, here are the three questions most likely to unlock the technical pain point" — it becomes irreplaceable. That specificity is not a UI problem or an AI quality problem. It is an input quality problem. Fix the input, and the output quality improves across every section without changing a single prompt template.
