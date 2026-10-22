"""AEGIS Central Configuration Module.

Loads and validates all environment variables using pydantic-settings.
Docs: docs/02-CONTRACTS.md & .agent/rules/01-architecture-and-contracts.md.
"""

from typing import Optional
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Graph Database Backend
    GRAPH_BACKEND: str = Field(default="networkx", description="Graph database backend ('networkx' or 'neo4j')")
    NEO4J_URI: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    NEO4J_USER: str = Field(default="neo4j", description="Neo4j username")
    NEO4J_PASSWORD: Optional[str] = Field(default=None, description="Neo4j password (required if GRAPH_BACKEND=neo4j)")

    # Security & Administration
    ADMIN_SHARED_SECRET: Optional[str] = Field(default=None, description="Secret token required for admin actions like /api/reset")

    # LLM Settings (LiteLLM abstraction)
    LLM_PROVIDER: str = Field(default="gemini", description="LLM provider: gemini, groq, or ollama")
    LLM_MODEL: str = Field(default="gemini/gemini-1.5-flash", description="Model identifier for LiteLLM")
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="API Key for Google Gemini")
    GROQ_API_KEY: Optional[str] = Field(default=None, description="API Key for Groq")
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", description="Base URL for local Ollama service")

    # Ingestion Settings
    GITHUB_TOKEN: Optional[str] = Field(default=None, description="GitHub Personal Access Token for ingestion")

    # Health Monitoring & Anomaly Detection Rules
    BASELINE_WINDOW: int = Field(default=5, description="Number of healthy probes to compute baseline latency")
    LATENCY_MULTIPLIER: float = Field(default=3.0, description="Multiplier over baseline to trigger latency anomaly")
    CONSECUTIVE_FAILURES: int = Field(default=2, description="Consecutive failure count to trigger outage anomaly")
    ERROR_RATE_THRESHOLD: float = Field(default=0.5, description="Error rate threshold in rolling window to trigger anomaly")
    COOLDOWN_SECONDS: float = Field(default=60.0, description="Cooldown seconds before emitting a new incident for the same service")
    MONITOR_INTERVAL_SEC: float = Field(default=3.0, description="Background monitor probe interval in seconds")
    MONITOR_TIMEOUT_SEC: float = Field(default=2.0, description="Per-probe HTTP timeout in seconds (shorter than interval)")

    # Server Configuration
    PORT: int = Field(default=8000, description="Port to bind the server")
    HOST: str = Field(default="0.0.0.0", description="Host to bind the server")

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
        if self.GRAPH_BACKEND.lower() == "neo4j" and not self.NEO4J_PASSWORD:
            raise ValueError("NEO4J_PASSWORD is required when GRAPH_BACKEND is 'neo4j'")
        if self.MONITOR_TIMEOUT_SEC >= self.MONITOR_INTERVAL_SEC:
            raise ValueError("MONITOR_TIMEOUT_SEC must be strictly shorter than MONITOR_INTERVAL_SEC")
        return self


settings = Settings()
