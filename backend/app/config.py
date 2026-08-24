from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LLM Evaluation & Red-Teaming API"
    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./data/evaluation.db"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    max_run_concurrency: int = Field(default=12, ge=1, le=50)
    max_active_runs: int = Field(default=4, ge=1, le=100)
    max_active_live_runs: int = Field(default=1, ge=1, le=20)
    max_live_run_prompts: int = Field(default=6, ge=1, le=600)
    max_demo_delay_ms: int = Field(default=50, ge=0, le=5_000)
    target_timeout_seconds: float = Field(default=45.0, gt=0, le=300)
    target_warmup_seconds: float = Field(default=180.0, ge=0, le=600)
    allow_private_target_urls: bool = False
    target_host_allowlist: str = ""
    openai_compatible_api_key: SecretStr | None = None
    huggingface_space_api_key: SecretStr | None = None
    huggingface_token: SecretStr | None = None
    live_run_access_key: SecretStr | None = None
    deepeval_model: str | None = None
    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "llm-evaluation"
    static_dir: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def target_host_allowlist_values(self) -> list[str]:
        return [host.strip().lower() for host in self.target_host_allowlist.split(",") if host.strip()]

    def resolved_static_dir(self) -> Path | None:
        if self.static_dir:
            return Path(self.static_dir).expanduser().resolve()
        backend_static = Path(__file__).resolve().parents[1] / "static"
        if backend_static.is_dir():
            return backend_static
        frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
        return frontend_dist if frontend_dist.is_dir() else None


@lru_cache
def get_settings() -> Settings:
    return Settings()
