"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """RAPTOR configuration. All values can be overridden via environment variables."""

    # Server
    port: int = 8000
    log_level: str = "INFO"
    version: str = "1.0.0"

    # Database
    database_path: str = "./data/raptor.db"

    # Anthropic API
    anthropic_api_key: str = ""

    # Model routing per agent role
    raptor_model_research: str = "claude-sonnet-4-20250514"
    raptor_model_structure: str = "claude-sonnet-4-20250514"
    raptor_model_writer: str = "claude-sonnet-4-20250514"
    raptor_model_reviewer: str = "claude-opus-4-20250514"
    raptor_model_production: str = "claude-sonnet-4-20250514"
    raptor_model_reflection: str = "claude-haiku-4-5-20251001"
    raptor_model_observatory: str = "claude-haiku-4-5-20251001"

    # Observability
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "raptor"

    # Research Agent
    semantic_scholar_api_key: str = ""
    raptor_rag_max_iterations: int = 3
    raptor_rag_min_sources: int = 5

    # Pipeline
    raptor_max_revision_cycles: int = 3
    raptor_reflection_enabled: bool = True

    model_config = {"env_prefix": "", "case_sensitive": False}

    def get_model_for_role(self, role: str) -> str:
        """Return the configured model for a given agent role."""
        mapping = {
            "research_strategist": self.raptor_model_research,
            "structure_architect": self.raptor_model_structure,
            "domain_writer": self.raptor_model_writer,
            "critical_reviewer": self.raptor_model_reviewer,
            "production_agent": self.raptor_model_production,
            "reflection": self.raptor_model_reflection,
            "observatory": self.raptor_model_observatory,
        }
        return mapping.get(role, self.raptor_model_research)


settings = Settings()
