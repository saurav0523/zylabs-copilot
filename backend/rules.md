# Backend Development Rules

1. **Lifespan Manager**: Use FastAPI lifespan instead of `@app.on_event("startup")` / `"shutdown"`.
2. **Logging**: No standard `print` statements in production. Use `structlog` to log details.
3. **Pydantic Schemas**: Every API endpoint request body and response must use Pydantic models.
4. **Environment settings**: No hardcoded API keys or server credentials. Access all configuration values from `config.py` loaded from `.env`.
5. **SQLAlchemy 2.0 Style**: Use async ORM sessions and `select()` constructs rather than deprecated query APIs.
6. **Exception wrappers**: All API endpoints must catch exceptions internally and return responses using the envelope format.
