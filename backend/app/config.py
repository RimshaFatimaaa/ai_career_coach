from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        # backend/.env must win over a stale DATABASE_URL left in the shell.
        return init_settings, dotenv_settings, env_settings, file_secret_settings

    app_name: str = "AI Career Coach"
    app_env: str = "development"
    secret_key: str = "dev-secret-change-me"
    frontend_url: str = "http://localhost:3000"
    database_url: str = "sqlite:///./career_coach.db"
    supabase_url: str = ""

    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_fast_model: str = "gpt-4o-mini"
    llm_premium_model: str = "gpt-4o-mini"

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_fast_model: str = "llama-3.1-8b-instant"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro: str = ""
    stripe_price_premium: str = ""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    embedding_api_key: str = ""
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_model: str = "text-embedding-3-small"

    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = "career-coach-docs"
    r2_endpoint: str = ""

    storage_dir: Path = ROOT / "storage"
    knowledge_dir: Path = ROOT.parent / "knowledge"
    access_token_expire_minutes: int = 60 * 24 * 7

    @field_validator(
        "llm_api_key",
        "embedding_api_key",
        "database_url",
        "secret_key",
        "groq_api_key",
        "gemini_api_key",
        "deepseek_api_key",
        "stripe_secret_key",
        "stripe_webhook_secret",
        "smtp_user",
        "smtp_password",
        "r2_account_id",
        "r2_access_key_id",
        "r2_secret_access_key",
        "r2_endpoint",
        mode="before",
    )
    @classmethod
    def strip_secrets(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @property
    def embedding_key(self) -> str:
        return self.embedding_api_key or self.llm_api_key

    @property
    def is_postgres(self) -> bool:
        return "postgres" in self.database_url

    @property
    def stripe_enabled(self) -> bool:
        return bool(self.stripe_secret_key)

    @property
    def smtp_enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_from)

    @property
    def r2_enabled(self) -> bool:
        return bool(self.r2_account_id and self.r2_access_key_id and self.r2_secret_access_key and self.r2_bucket)

    @property
    def r2_endpoint_url(self) -> str:
        if self.r2_endpoint:
            return self.r2_endpoint.rstrip("/")
        if not self.r2_account_id:
            return ""
        return f"https://{self.r2_account_id}.r2.cloudflarestorage.com"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    return settings
