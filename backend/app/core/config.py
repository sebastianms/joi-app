from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./joi_app.db"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    JSON_UPLOAD_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB

    ANTHROPIC_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None

    LLM_MODEL_SQL: str = "anthropic/claude-haiku-4-5-20251001"
    LLM_MODEL_JSON: str = "anthropic/claude-haiku-4-5-20251001"
    LLM_MODEL_CHAT: str = "anthropic/claude-haiku-4-5-20251001"
    LLM_MODEL_WIDGET: str = "anthropic/claude-haiku-4-5-20251001"

    RAG_DEFAULT_ENABLED: bool = True
    QUERY_TIMEOUT_SECONDS: int = 10
    WIDGET_GENERATION_TIMEOUT_SECONDS: int = 8
    MAX_ROWS_PER_EXTRACTION: int = 1000
    TRACE_PREVIEW_ROWS: int = 10

    MOCK_LLM_RESPONSES: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
