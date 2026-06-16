# Product Improvements

## 1. Five Weaknesses in the Current Design

**Reports go stale immediately.** Once a report is generated it's frozen. A company can announce a funding round, lose their CEO, or ship a major product update the next morning — and the report still shows yesterday's picture. There's no refresh, no staleness indicator, nothing. For a sales context where timing is everything, this is a real problem.

**The research objective field is too open-ended.** Right now it's a freeform text box and most users will write something like "sales call prep" which tells the AI almost nothing useful. The system doesn't know if you're an SDR doing cold outreach, an AE going into a renewal, or a founder exploring a partnership. The output ends up generic because the input is generic.

**The report is read-only.** It generates a wall of text and that's it. There's no way to highlight something, add a note to yourself, collapse sections you don't care about, or mark something as "already knew this." Sales reps don't just read — they annotate, they prioritize, they skip things. The current UI doesn't let them do any of that.

**It's completely disconnected from existing workflows.** The people who need this tool already have Salesforce open, Google Calendar reminders firing, Slack threads running. After reading the report they have to manually copy insights into their CRM or their meeting notes. That manual step kills adoption — if it doesn't save time end-to-end, reps won't build a habit around it.

**No memory between sessions.** Research the same company twice and the second run starts completely from scratch. There's no "last time you looked at Acme, the QA score was low because their website was blocked" or "you previously noted they were hiring heavily in APAC." Account management involves returning to the same companies repeatedly, and right now each visit is a cold start.

## 2. Top 3 Improvements to Build Next

**Structured meeting context (fixes weakness #2)**

Instead of a freeform objective field, ask 3 quick questions before running the workflow: what's your role, what kind of meeting is this, and what does your product do in one sentence. These answers get injected directly into the Planner and Reporter prompts. The difference in output quality is night and day — instead of "here's everything about this company," the report says "here's what matters for an AE going into a first demo with an engineering team." That specificity is what makes the tool feel indispensable rather than just convenient.

**Section-level refresh (fixes weakness #1)**

A "Refresh" button per section that re-runs only the Researcher and Analyst nodes scoped to that topic, filtered to content from the last 30 days. Users keep their annotated report but get fresh data where things change fast — funding news, executive moves, product launches. The LangGraph subgraph API supports this without major restructuring.

**One-click CRM export (fixes weakness #4)**

A "Push to Salesforce" button that maps report sections to CRM fields automatically: Company Overview → Account Description, Business Signals → Activity log entry, Discovery Questions → Next Steps tasks. This turns the tool from something you use in isolation into something that fits into the workflow that already exists. That's where retention lives.

## 3. Who Buys It, Who Uses It, Why They Pay

The buyer is a VP of Sales or Head of Revenue at a B2B company with a sales team of 10-200 people. They're paying for rep productivity tools constantly — this fits the same budget as Gong, Outreach, or Clari. What gets their attention is time saved per rep per week, not features.

The users are AEs and SDRs who currently spend 20-40 minutes Googling before an important call, pulling from 5 different tabs, and still walking in under-prepared. Half of them skip the research entirely when the calendar is full.

Why they pay: the math is straightforward. A team of 10 AEs doing 5 research sessions per week each saves roughly 25 hours of research time weekly. At a blended rep cost of $80/hour, that's $2000/week in recovered time — way more than a $300/month subscription. The ROI conversation is easy.

## 4. Success Metrics

Sessions per active user per week — target 3+. If people are using it less than 3 times a week they're not making it a habit, and a tool that isn't a habit doesn't stick.

Report quality score from the internal QA node — target above 0.75 average. Below that and the reports aren't good enough to be trusted.

User thumbs up/down rating after each report — target 80%+ positive. This is the leading indicator before you have CRM attribution data.

Workflow completion rate (successful runs / total runs) — target 95%+. Every failure is a rep who walked into a meeting unprepared and blames the tool.

Time saved per session self-reported via a quick post-report prompt — target 20+ minutes. If users don't feel the time save, they'll stop using it.

## 5. Four-Week AI Roadmap

**Week 1** — Structured meeting context intake. Replace the freeform objective field with 3 targeted dropdowns + a short free text box. Update all LLM prompts to consume structured context. Measure report quality score improvement.

**Week 2** — Section-level refresh. Build the LangGraph subgraph for selective re-execution. Add "Last updated" timestamps per section. Ship a "Refresh this section" button in the UI.

**Week 3** — Salesforce + HubSpot export via OAuth. Map report fields to standard CRM objects. Ship the "Push to CRM" button. Track whether export usage correlates with retention.

**Week 4** — Account memory layer. Embed past report sections into pgvector. Pull relevant context from previous sessions on the same company and inject it into new runs. Test with power users who research the same accounts repeatedly.

## 6. Biggest Cost, Scaling, and Reliability Risks

**Cost** — LLM API spend scales directly with usage. Each research session makes 4-5 LLM calls with large context windows (scraped content is long). At current token prices, 10,000 sessions/month gets expensive fast. The immediate mitigation is aggressive Firecrawl caching (already implemented) and adding a "quick mode" that only scrapes the homepage instead of 8-10 URLs.

**Scaling** — The workflow runs as an in-process FastAPI background task. That works fine under low concurrency but starts breaking when multiple long-running workflows compete for the same threads. The fix is moving to a proper task queue (Celery + Redis), but that's not in the current MVP.

**Reliability** — There are three external dependencies that can each fail independently: Firecrawl, the LLM provider, and the database. A Firecrawl outage during a sales team's busy morning would surface as a wave of failed reports with no clear user message. Need circuit breakers, better error messaging, and a status page showing dependency health.

## 7. Feature I'd Remove

The freeform research objective text field — not the concept, just the current implementation.

It creates false confidence. Users think their objective is being "understood" by the AI, but a vague objective like "sales call" contributes almost nothing to the output quality. It's input theater. Replacing it with 3 structured dropdowns gives the AI genuinely useful context and takes the cognitive burden off the user. The field as-is is worse than nothing because it implies personalization that isn't really happening.

## 8. Feature I'd Add

A "Red Flags" section in the report that's separate from risks and challenges.

Risks and challenges are things you already know to look for. Red flags are things you might be inclined to ignore — recent executive departures, Glassdoor patterns suggesting internal chaos, product reviews mentioning support issues, funding rounds that are suspiciously small or haven't happened in 3 years. Sales reps are optimistic by nature and often rationalize away signals that a deal is going to be hard. A dedicated section that explicitly surfaces red flags makes the tool honest in a way that's genuinely valuable for rep productivity, not just for closing deals faster but for closing the *right* deals faster.

## 9. First 90-Day Roadmap

**Days 1-30 — Validate with real users.** Get the MVP in front of 15-20 sales reps from 4-5 companies (mix of sizes and verticals). Run sessions where they use the tool before an actual call and then debrief after. Watch for which report sections they read first, which they skip, and whether the follow-up chat gets used. Don't build anything new — just observe.

**Days 31-60 — Fix the biggest friction points.** Based on what the first month shows, ship structured context intake (almost certainly the highest impact change based on the generic-output problem) and fix whatever completion rate issues surfaced in production. Also add the thumbs up/down rating to start collecting quality signal at scale.

**Days 61-90 — Start the monetization motion.** Introduce a paid tier. Ship CRM export as a paid feature. Start having commercial conversations with the companies whose reps are using it most. Target: at least 3 teams on paid plans by day 90, and a clear enough retention pattern that you can model growth.

## 10. What I'd Change First

The research objective input.

Everything else about the product — the LangGraph workflow, the WebSocket progress UI, the report structure — is solid engineering. The bottleneck isn't technical, it's the quality of the input going into the LLM. A rep typing "prepare for call" into a freeform box gets a report that could apply to any company in any industry. The same rep selecting "AE / First Demo / Selling a sales analytics platform" gets a report that's actually calibrated to their situation.

That change doesn't require touching the backend workflow at all. It's a frontend form change and a prompt update. The ROI on it is higher than anything else on this list because it makes every single report better immediately, not just for edge cases.
