# ZyLabs AI Research Copilot Backend

FastAPI Python backend serving the LangGraph execution engine, DB persistence, and real-time WebSockets progress broadcaster.

## Run Locally

```bash
# Set up virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
uvicorn main:app --reload --port 8000
```

## Folder Structure

- `api/`: Endpoint routers for sessions, workflow trigger, follow-up chat, and WebSocket handlers.
- `db/`: SQLAlchemy schemas and session generator.
- `services/`: Wrappers for firecrawl API client, LLM providers, and WebSocket registry broadcaster.
- `workflow/`: StateGraph topology definitions and node tasks.
