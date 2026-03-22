"""Abstract base agent with common instrumentation, token recording, and decision logging."""

import json
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.core.database import get_db
from app.models.constants import AgentRole, ArtifactType, ArtifactStatus
from app.models.envelope import ArtifactEnvelope, ArtifactMetadata, ReflectionResult
from app.services.ai.client import ai_client
from app.services.ai.prompts.base import build_system_prompt
from app.services import artifact_service
from app.services.pipeline.websocket_manager import ws_manager

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all RAPTOR agents.

    Provides:
    - LLM completion via ai_client
    - Self-reflection checkpoint
    - Decision logging
    - Artifact envelope construction
    - Progress broadcasting
    """

    role: AgentRole
    artifact_type: ArtifactType

    def __init__(self):
        self.logger = logging.getLogger(f"agent.{self.role}")

    @abstractmethod
    async def execute(self, project: Any, venue: Any) -> ArtifactEnvelope:
        """Execute the agent's task. Returns an ArtifactEnvelope."""
        ...

    async def complete(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        project_id: str | None = None,
        operation: str = "completion",
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Run an LLM completion with this agent's model routing."""
        if model is None:
            model = settings.get_model_for_role(self.role)

        return ai_client.complete(
            messages=messages,
            model=model,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            agent_role=self.role,
            project_id=project_id,
            operation=operation,
        )

    async def self_reflect(
        self,
        output: str,
        reflection_prompt: str,
        project_id: str | None = None,
    ) -> ReflectionResult:
        """Run a self-reflection checkpoint using Haiku."""
        if not settings.raptor_reflection_enabled:
            return ReflectionResult(passed=True, reflection_model="disabled")

        model = settings.get_model_for_role("reflection")
        system = "You are a quality checker. Evaluate the output against the given criteria. Respond with JSON: {\"passed\": true/false, \"issues\": [\"issue1\", ...]}"

        result = ai_client.complete(
            messages=[
                {"role": "user", "content": f"## Criteria\n{reflection_prompt}\n\n## Output to Evaluate\n{output[:3000]}"}
            ],
            model=model,
            system=system,
            max_tokens=1024,
            temperature=0.0,
            agent_role=f"{self.role}.reflection",
            project_id=project_id,
            operation="self_reflection",
        )

        try:
            # Parse the reflection response
            content = result["content"]
            # Try to extract JSON from the response
            if "{" in content:
                json_str = content[content.index("{"):content.rindex("}") + 1]
                parsed = json.loads(json_str)
                return ReflectionResult(
                    passed=parsed.get("passed", True),
                    issues_found=parsed.get("issues", []),
                    reflection_model=model,
                    reflection_tokens=result["input_tokens"] + result["output_tokens"],
                )
        except (json.JSONDecodeError, ValueError):
            self.logger.warning("[%s] Failed to parse reflection response", self.role)

        return ReflectionResult(passed=True, reflection_model=model, reflection_tokens=result.get("output_tokens", 0))

    def build_envelope(
        self,
        project_id: str,
        payload: dict[str, Any],
        metadata: ArtifactMetadata,
        target_agent: str | None = None,
        quality_scores: dict[str, float] | None = None,
        reflection_result: ReflectionResult | None = None,
        venue_context: dict[str, Any] | None = None,
    ) -> ArtifactEnvelope:
        """Build an ArtifactEnvelope for this agent's output."""
        version = artifact_service.get_next_version(project_id, self.artifact_type, self.role)

        return ArtifactEnvelope(
            artifact_id=str(uuid.uuid4()),
            artifact_type=self.artifact_type,
            source_agent=self.role,
            target_agent=target_agent,
            project_id=project_id,
            version=version,
            venue_context=venue_context or {},
            payload=payload,
            metadata=metadata,
            quality_scores=quality_scores or {},
            reflection_result=reflection_result,
            status=ArtifactStatus.SUBMITTED,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def log_decision(
        self,
        project_id: str,
        decision: str,
        rationale: str,
        confidence: float = 0.0,
        alternatives: list[str] | None = None,
    ) -> None:
        """Log a decision to the decision_logs table."""
        try:
            db = get_db()
            db.execute(
                """INSERT INTO decision_logs (id, project_id, agent, decision, rationale,
                   alternatives_considered, confidence)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), project_id, self.role, decision, rationale,
                 json.dumps(alternatives) if alternatives else None, confidence),
            )
            db.commit()
        except Exception as e:
            self.logger.warning("[%s] Failed to log decision: %s", self.role, e)

    async def broadcast_progress(self, project_id: str, message: str, progress_pct: int = 0) -> None:
        """Send a progress update via WebSocket."""
        await ws_manager.send_progress(project_id, self.role, message, progress_pct)
