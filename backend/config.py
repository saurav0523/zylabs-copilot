import os
from typing import Optional
from contextvars import ContextVar
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

request_id_var: ContextVar[str] = ContextVar("request_id", default="")

class Settings(BaseSettings):
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/zylabs")
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    
    FIRECRAWL_API_KEY: str = Field(default="")
    TAVILY_API_KEY: Optional[str] = Field(default=None)
    
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    GEMINI_API_KEY: Optional[str] = Field(default=None)
    
    OPENROUTER_API_KEY: str = Field(default="")
    OPENROUTER_PRIMARY_MODEL: str = Field(default="openrouter/free")
    OPENROUTER_FALLBACK_MODEL: str = Field(default="openrouter/free")
    NODE_MODEL_PLANNER:  str = Field(default="openrouter/free")
    NODE_MODEL_ANALYST:  str = Field(default="openrouter/free")
    NODE_MODEL_QA:       str = Field(default="openrouter/free")
    NODE_MODEL_REPORTER: str = Field(default="openrouter/free")
    NODE_MODEL_CHAT:     str = Field(default="openrouter/free")
    
    LOG_LEVEL: str = Field(default="INFO")
    MAX_RETRY_COUNT: int = Field(default=2)
    QA_QUALITY_THRESHOLD: float = Field(default=0.7)
    MAX_PAGES_PER_SESSION: int = Field(default=10)
    
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
