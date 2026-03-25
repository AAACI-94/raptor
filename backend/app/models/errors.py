"""RAPTOR error hierarchy. Typed exceptions for structured error handling."""

from typing import Any


class RaptorError(Exception):
    """Base error for all RAPTOR operations. Carries context for diagnosis."""

    def __init__(
        self,
        message: str,
        agent_role: str = "",
        project_id: str = "",
        is_transient: bool = False,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.agent_role = agent_role
        self.project_id = project_id
        self.is_transient = is_transient
        self.context = context or {}


class ParseError(RaptorError):
    """LLM output not valid JSON or missing expected fields."""

    def __init__(self, message: str, raw_output: str = "", **kwargs: Any):
        super().__init__(message, is_transient=True, **kwargs)
        self.raw_output = raw_output


class ProviderError(RaptorError):
    """AI provider unavailable (Ollama down, Claude CLI failing, auth issues)."""

    def __init__(self, message: str, provider: str = "", **kwargs: Any):
        super().__init__(message, is_transient=True, **kwargs)
        self.provider = provider


class AgentTimeoutError(RaptorError):
    """Agent exceeded execution time limit."""

    def __init__(self, message: str, timeout_s: float = 0, **kwargs: Any):
        super().__init__(message, is_transient=True, **kwargs)
        self.timeout_s = timeout_s


class QualityDegradationError(RaptorError):
    """Quality scores dropped below acceptable threshold."""

    def __init__(self, message: str, scores: dict[str, float] | None = None, **kwargs: Any):
        super().__init__(message, is_transient=False, **kwargs)
        self.scores = scores or {}


class CostAnomalyError(RaptorError):
    """Token usage exceeded expected range for this agent."""

    def __init__(self, message: str, expected_tokens: int = 0, actual_tokens: int = 0, **kwargs: Any):
        super().__init__(message, is_transient=False, **kwargs)
        self.expected_tokens = expected_tokens
        self.actual_tokens = actual_tokens


class ValidationError(RaptorError):
    """Input to agent failed validation."""

    def __init__(self, message: str, field: str = "", **kwargs: Any):
        super().__init__(message, is_transient=False, **kwargs)
        self.field = field
