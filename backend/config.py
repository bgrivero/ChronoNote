from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/chrononote"
    AUTO_FALLBACK_SQLITE: bool = True
    SQLITE_FALLBACK_URL: str = "sqlite:///./chrononote.db"
    APP_ENV: str = "development"

    # Google Authentication & Personal Access Control
    GOOGLE_CLIENT_ID: str = ""
    ALLOWED_GOOGLE_EMAILS: str = ""
    AUTH_SECRET_KEY: str = "chrononote-personal-secret-key-change-in-production"
    AUTH_REQUIRED: bool = False

    # Optional Gemini Vision API Key for high-accuracy cursive handwriting OCR
    GEMINI_API_KEY: str = ""


settings = Settings()
