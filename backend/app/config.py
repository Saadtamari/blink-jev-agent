from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent
DATA_DIR = REPO_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    llm_planner_model: str = "google/gemini-2.5-flash"
    llm_fast_model: str = "google/gemini-2.5-flash"
    llm_vision_model: str = "google/gemini-2.5-flash"

    llm_provider: str = "openrouter"  # openrouter | offline (scripted, no key; pair with JEV_PROVIDER=mock)
    jev_provider: str = "jev"  # jev | mock | llm_fallback
    jev_model: str = "typesafe/jev-1.14"
    jev_decisions_url: str = "https://openrouter.ai/api/alpha/decisions"
    jev_image_mode: str = "image_url"  # image_url | assets

    max_parallel_branches: int = 4
    conf_act: float = 0.85
    conf_check: float = 0.60
    max_step_retries: int = 2
    step_timeout_s: float = 30
    handoff_timeout_s: float = 600
    screenshot_max_width: int = 1280
    viewport_width: int = 1366
    viewport_height: int = 900
    headless: bool = False
    demo_mode: bool = False
    domain_blocklist: str = ""

    host: str = "127.0.0.1"
    port: int = 8000
    frontend_origin: str = "http://localhost:3000"

    @property
    def blocked_domains(self) -> list[str]:
        return [d.strip().lower() for d in self.domain_blocklist.split(",") if d.strip()]

    def public(self) -> dict:
        """Config safe to show in the UI (no secrets)."""
        return {
            "llm_planner_model": self.llm_planner_model,
            "llm_fast_model": self.llm_fast_model,
            "llm_vision_model": self.llm_vision_model,
            "jev_provider": self.jev_provider,
            "llm_provider": self.llm_provider,
            "jev_model": self.jev_model,
            "max_parallel_branches": self.max_parallel_branches,
            "conf_act": self.conf_act,
            "conf_check": self.conf_check,
            "headless": self.headless,
            "demo_mode": self.demo_mode,
            "has_api_key": bool(self.openrouter_api_key),
            "viewport": {"width": self.viewport_width, "height": self.viewport_height},
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
