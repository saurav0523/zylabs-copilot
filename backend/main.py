import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import structlog

from backend.config import settings, request_id_var
from backend.logging_config import setup_logging

setup_logging(settings.LOG_LEVEL)
logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up", host=settings.HOST, port=settings.PORT)
    yield
    logger.info("Application shutting down")

app = FastAPI(
    title="ZyLabs AI Research Copilot API",
    lifespan=lifespan
)

# CORS middleware config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify front-end origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware to add unique request ID to context
@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    req_id = request_id_var.get()
    if not req_id:
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = request_id_var.set(req_id)
    else:
        token = None
    structlog.contextvars.bind_contextvars(request_id=req_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response
    finally:
        structlog.contextvars.clear_contextvars()
        if token:
            request_id_var.reset(token)

# Exception handlers adhering to envelope pattern
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    req_id = request_id_var.get()
    logger.warn("HTTP Exception raised", status_code=exc.status_code, detail=exc.detail, request_id=req_id)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "code": f"HTTP_ERROR_{exc.status_code}",
            "request_id": req_id
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = request_id_var.get()
    logger.warn("Validation error", errors=exc.errors(), request_id=req_id)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation failed: " + str(exc.errors()),
            "code": "VALIDATION_ERROR",
            "request_id": req_id
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    req_id = request_id_var.get()
    logger.error("Unhandled exception", error=str(exc), exc_info=True, request_id=req_id)
    
    exc_str = str(exc).lower()
    if any(dep in exc_str for dep in ["firecrawl", "openai", "anthropic", "connection refused"]):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        code = "DEPENDENCY_UNAVAILABLE"
        error_msg = "A required external service is currently unavailable."
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        code = "INTERNAL_SERVER_ERROR"
        error_msg = "An unexpected error occurred."

    return JSONResponse(
        status_code=status_code,
        content={
            "error": error_msg,
            "code": code,
            "request_id": req_id
        }
    )

# Routers imports and registration
from backend.api.sessions import router as sessions_router
from backend.api.workflow import router as workflow_router
from backend.api.chat import router as chat_router
from backend.api.websocket import router as ws_router

app.include_router(sessions_router, prefix="/api")
app.include_router(workflow_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(ws_router)  # WebSocket router maps to /ws/session/{id} directly
