"""Sentinel: wraps agent execution with failure detection, diagnosis, and auto-remediation.

This is middleware, not a pipeline stage. It transparently wraps every agent.execute() call
in the orchestrator with monitoring, error classification, and automatic fix attempts.
"""

import json
import logging
import time
import uuid
from typing import Any

from app.core.config import settings
from app.core.database import get_db
from app.models.constants import DiagnosticEventType, DiagnosticSeverity, RemediationAction
from app.models.diagnostic import Diagnosis
from app.models.envelope import ArtifactEnvelope
from app.models.errors import (
    RaptorError, ParseError, ProviderError, AgentTimeoutError,
    QualityDegradationError, CostAnomalyError,
)
from app.services.pipeline.diagnostic import diagnostic_agent
from app.services.pipeline.remediation import remediation_engine
from app.services.pipeline.websocket_manager import ws_manager

logger = logging.getLogger(__name__)


class Sentinel:
    """Wraps agent execution with failure detection, timing, and anomaly checks.

    Integration: orchestrator calls sentinel.execute_with_protection() instead of agent.execute().
    If sentinel is disabled via config, the orchestrator falls back to direct agent.execute().
    """

    async def execute_with_protection(
        self,
        agent: Any,
        project: Any,
        venue: Any,
        project_id: str,
    ) -> ArtifactEnvelope:
        """Execute an agent with full sentinel protection."""
        correlation_id = str(uuid.uuid4())
        agent_role = getattr(agent, "role", "unknown")

        # Pre-flight: check provider health
        if not await self._preflight_check(project_id, agent_role, correlation_id):
            logger.warning("[sentinel] Pre-flight failed for %s, attempting remediation", agent_role)

        # Execute with monitoring
        start = time.monotonic()
        try:
            envelope = await agent.execute(project, venue)
            duration_ms = int((time.monotonic() - start) * 1000)

            # Post-execution quality checks
            await self._post_execution_check(envelope, agent_role, project_id, correlation_id, duration_ms)

            return envelope

        except Exception as error:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.error("[sentinel] Agent %s failed after %dms: %s", agent_role, duration_ms, error)

            # Classify the error
            context = {
                "agent_role": agent_role,
                "project_id": project_id,
                "duration_ms": duration_ms,
                "project_title": getattr(project, "title", ""),
                "venue": getattr(venue, "display_name", "") if venue else "",
            }

            # Wrap in RaptorError if it isn't one already
            if not isinstance(error, RaptorError):
                if "timeout" in str(error).lower():
                    error = AgentTimeoutError(str(error), agent_role=agent_role, project_id=project_id)
                elif "json" in str(error).lower() or "parse" in str(error).lower():
                    error = ParseError(str(error), agent_role=agent_role, project_id=project_id)
                elif "connection" in str(error).lower() or "refused" in str(error).lower():
                    error = ProviderError(str(error), agent_role=agent_role, project_id=project_id)

            # Diagnose
            diagnosis = await diagnostic_agent.diagnose(error, agent_role, project_id, context)

            # Log the detection event
            self._log_event(project_id, correlation_id, DiagnosticEventType.AGENT_FAILURE,
                           diagnosis.severity, agent_role, error, diagnosis)

            # Broadcast to frontend
            await ws_manager.broadcast(project_id, {
                "event": "sentinel_detected",
                "agent": agent_role,
                "error_type": diagnosis.error_class,
                "severity": diagnosis.severity,
                "root_cause": diagnosis.root_cause[:100],
                "correlation_id": correlation_id,
            })

            # Attempt remediation
            raw_output = getattr(error, "raw_output", "")
            for attempt in range(settings.raptor_max_remediation_attempts):
                action = diagnosis.recommended_actions[attempt] if attempt < len(diagnosis.recommended_actions) else RemediationAction.ESCALATE_TO_USER

                if action == RemediationAction.ESCALATE_TO_USER:
                    break

                await ws_manager.broadcast(project_id, {
                    "event": "remediation_started",
                    "agent": agent_role,
                    "action": action,
                    "attempt": attempt + 1,
                    "correlation_id": correlation_id,
                })

                result = await remediation_engine.attempt(
                    diagnosis, agent, project, venue, attempt, raw_output,
                )

                if result.success:
                    self._log_event(project_id, correlation_id, DiagnosticEventType.REMEDIATION_SUCCESS,
                                   DiagnosticSeverity.LOW, agent_role, error, diagnosis,
                                   remediation_action=action, attempt=attempt + 1, success=True)

                    await ws_manager.broadcast(project_id, {
                        "event": "remediation_success",
                        "agent": agent_role,
                        "action": action,
                        "attempt": attempt + 1,
                        "correlation_id": correlation_id,
                    })

                    # If remediation returned an envelope, use it
                    if result.envelope and isinstance(result.envelope, dict):
                        if "artifact_id" in result.envelope:
                            return ArtifactEnvelope(**result.envelope)
                        # JSON repair case: envelope is just the fixed payload
                        # Re-execute with the knowledge that a simple retry worked
                        envelope = await agent.execute(project, venue)
                        return envelope

                    # Remediation succeeded via re-execution
                    envelope = await agent.execute(project, venue)
                    return envelope

                self._log_event(project_id, correlation_id, DiagnosticEventType.REMEDIATION_FAILED,
                               diagnosis.severity, agent_role, error, diagnosis,
                               remediation_action=action, attempt=attempt + 1, success=False)

                await ws_manager.broadcast(project_id, {
                    "event": "remediation_retry",
                    "agent": agent_role,
                    "action": action,
                    "attempt": attempt + 1,
                    "correlation_id": correlation_id,
                })

            # All attempts exhausted: escalate to user
            self._log_event(project_id, correlation_id, DiagnosticEventType.USER_ESCALATION,
                           DiagnosticSeverity.CRITICAL, agent_role, error, diagnosis)

            await ws_manager.broadcast(project_id, {
                "event": "user_escalation",
                "agent": agent_role,
                "diagnosis": {
                    "root_cause": diagnosis.root_cause,
                    "severity": diagnosis.severity,
                    "classification": diagnosis.classification,
                    "attempts_made": min(settings.raptor_max_remediation_attempts, len(diagnosis.recommended_actions)),
                },
                "correlation_id": correlation_id,
            })

            # Re-raise the original error
            raise

    async def _preflight_check(self, project_id: str, agent_role: str, correlation_id: str) -> bool:
        """Verify AI provider is healthy before starting agent execution."""
        from app.services.ai.ollama import check_ollama
        from app.services.ai.claude_cli import check_claude_cli
        from app.services.ai import router as ai_router

        provider = ai_router.get_provider()
        if provider == "claude-cli":
            return check_claude_cli()
        elif provider == "ollama":
            return check_ollama()
        return False

    async def _post_execution_check(self, envelope: ArtifactEnvelope, agent_role: str,
                                     project_id: str, correlation_id: str, duration_ms: int) -> None:
        """Check the output for quality and cost anomalies."""
        # Check reflection failure
        if envelope.reflection_result and not envelope.reflection_result.passed:
            logger.warning("[sentinel] Self-reflection failed for %s: %s",
                          agent_role, envelope.reflection_result.issues_found)
            self._log_event(
                project_id, correlation_id, DiagnosticEventType.QUALITY_DEGRADATION,
                DiagnosticSeverity.LOW, agent_role,
                QualityDegradationError("Self-reflection failed", agent_role=agent_role),
                Diagnosis(correlation_id=correlation_id, error_class="QualityDegradation",
                         root_cause="Self-reflection checkpoint failed",
                         classification="quality", severity=DiagnosticSeverity.LOW,
                         confidence=0.7),
            )

        # Check for empty payload
        if not envelope.payload or envelope.payload.get("raw_content"):
            logger.warning("[sentinel] Agent %s produced empty or raw payload", agent_role)

        # Cost anomaly check (compare to historical average)
        if envelope.metadata.estimated_cost_usd > 0:
            avg_cost = self._get_avg_cost(agent_role)
            if avg_cost > 0 and envelope.metadata.estimated_cost_usd > avg_cost * settings.raptor_cost_anomaly_multiplier:
                logger.warning("[sentinel] Cost anomaly: %s cost $%.4f (avg: $%.4f, threshold: %.1fx)",
                              agent_role, envelope.metadata.estimated_cost_usd, avg_cost,
                              settings.raptor_cost_anomaly_multiplier)

    def _get_avg_cost(self, agent_role: str) -> float:
        """Get average cost for an agent from historical data."""
        try:
            db = get_db()
            row = db.execute(
                "SELECT AVG(estimated_cost_usd) as avg_cost FROM token_usage WHERE agent = ?",
                (agent_role,),
            ).fetchone()
            return row["avg_cost"] or 0.0
        except Exception:
            return 0.0

    def _log_event(
        self,
        project_id: str,
        correlation_id: str,
        event_type: str,
        severity: str,
        agent_role: str,
        error: Exception,
        diagnosis: Diagnosis,
        remediation_action: str = "",
        attempt: int = 0,
        success: bool | None = None,
    ) -> None:
        """Store a diagnostic event in the database."""
        try:
            db = get_db()
            db.execute(
                """INSERT INTO diagnostic_events (id, project_id, correlation_id, event_type,
                   severity, agent_role, error_class, error_message, diagnosis,
                   remediation_action, remediation_attempt, remediation_success)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), project_id, correlation_id, event_type,
                 severity, agent_role, type(error).__name__, str(error)[:500],
                 json.dumps(diagnosis.model_dump()),
                 remediation_action, attempt, success),
            )
            db.commit()
        except Exception as e:
            logger.warning("[sentinel] Failed to log diagnostic event: %s", e)


# Singleton
sentinel = Sentinel()
