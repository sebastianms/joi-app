from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./joi_app.db"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    JSON_UPLOAD_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
