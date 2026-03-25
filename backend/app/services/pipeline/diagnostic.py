"""Diagnostic Agent: classifies errors and determines root cause.

Uses heuristic rules for ~80% of cases and Ollama LLM for ambiguous failures.
Always uses Ollama (never Claude CLI) to avoid diagnosing the tool that's broken.
"""

import json
import logging
import uuid
from typing import Any

from app.core.config import settings
from app.models.constants import DiagnosticSeverity, RemediationAction, DiagnosticEventType
from app.models.diagnostic import Diagnosis
from app.models.errors import (
    RaptorError, ParseError, ProviderError, AgentTimeoutError,
    QualityDegradationError, CostAnomalyError, ValidationError,
)

logger = logging.getLogger(__name__)

# Heuristic classification rules: exception type -> (classification, severity, actions)
HEURISTIC_RULES: dict[type, tuple[str, str, list[str]]] = {
    ParseError: (
        "transient",
        DiagnosticSeverity.MEDIUM,
        [RemediationAction.JSON_REPAIR, RemediationAction.SIMPLIFY_PROMPT, RemediationAction.RETRY],
    ),
    ProviderError: (
        "environmental",
        DiagnosticSeverity.HIGH,
        [RemediationAction.SWITCH_PROVIDER, RemediationAction.RETRY_WITH_BACKOFF],
    ),
    AgentTimeoutError: (
        "transient",
        DiagnosticSeverity.MEDIUM,
        [RemediationAction.INCREASE_TIMEOUT, RemediationAction.REDUCE_INPUT, RemediationAction.SWITCH_PROVIDER],
    ),
    QualityDegradationError: (
        "quality",
        DiagnosticSeverity.MEDIUM,
        [RemediationAction.INJECT_FEEDBACK, RemediationAction.RETRY],
    ),
    CostAnomalyError: (
        "structural",
        DiagnosticSeverity.LOW,
        [RemediationAction.REDUCE_INPUT, RemediationAction.SIMPLIFY_PROMPT],
    ),
    ValidationError: (
        "structural",
        DiagnosticSeverity.HIGH,
        [RemediationAction.ESCALATE_TO_USER],
    ),
}

# String patterns in error messages -> classification overrides
MESSAGE_PATTERNS: list[tuple[str, str, str, list[str]]] = [
    ("not authenticated", "structural", DiagnosticSeverity.CRITICAL, [RemediationAction.ESCALATE_TO_USER]),
    ("connection refused", "environmental", DiagnosticSeverity.HIGH, [RemediationAction.SWITCH_PROVIDER]),
    ("rate limit", "transient", DiagnosticSeverity.MEDIUM, [RemediationAction.RETRY_WITH_BACKOFF]),
    ("model not found", "environmental", DiagnosticSeverity.HIGH, [RemediationAction.SWITCH_PROVIDER]),
    ("context length exceeded", "structural", DiagnosticSeverity.MEDIUM, [RemediationAction.REDUCE_INPUT]),
    ("JSON", "transient", DiagnosticSeverity.MEDIUM, [RemediationAction.JSON_REPAIR]),
]


class DiagnosticAgent:
    """Classifies errors and determines root cause.

    Two-tier classification:
    1. Heuristic pre-classifier (no LLM, handles ~80% of cases)
    2. Ollama LLM classifier (for ambiguous cases, always local)
    """

    async def diagnose(self, error: Exception, agent_role: str, project_id: str,
                       context: dict[str, Any] | None = None) -> Diagnosis:
        """Analyze an error and produce a structured diagnosis."""
        correlation_id = str(uuid.uuid4())

        # Tier 1: Heuristic classification
        diagnosis = self._heuristic_classify(error, correlation_id, agent_role)
        if diagnosis and diagnosis.confidence >= 0.8:
            logger.info("[diagnostic] Heuristic diagnosis: %s (%s, confidence %.1f)",
                       diagnosis.root_cause[:80], diagnosis.classification, diagnosis.confidence)
            return diagnosis

        # Tier 2: LLM classification for ambiguous cases
        diagnosis = await self._llm_classify(error, correlation_id, agent_role, context)
        logger.info("[diagnostic] LLM diagnosis: %s (%s, confidence %.1f)",
                   diagnosis.root_cause[:80], diagnosis.classification, diagnosis.confidence)
        return diagnosis

    def _heuristic_classify(self, error: Exception, correlation_id: str, agent_role: str) -> Diagnosis | None:
        """Fast heuristic classification based on exception type and message patterns."""
        error_class = type(error).__name__
        error_msg = str(error).lower()

        # Check typed RAPTOR errors
        if isinstance(error, RaptorError):
            rule = HEURISTIC_RULES.get(type(error))
            if rule:
                classification, severity, actions = rule
                return Diagnosis(
                    correlation_id=correlation_id,
                    error_class=error_class,
                    root_cause=str(error),
                    classification=classification,
                    severity=severity,
                    recommended_actions=actions,
                    context_notes=f"Heuristic match on {error_class}",
                    confidence=0.9,
                )

        # Check message patterns
        for pattern, classification, severity, actions in MESSAGE_PATTERNS:
            if pattern.lower() in error_msg:
                return Diagnosis(
                    correlation_id=correlation_id,
                    error_class=error_class,
                    root_cause=f"{error_class}: {str(error)[:200]}",
                    classification=classification,
                    severity=severity,
                    recommended_actions=actions,
                    context_notes=f"Pattern match: '{pattern}' found in error message",
                    confidence=0.85,
                )

        # Generic exception: low confidence, needs LLM
        return Diagnosis(
            correlation_id=correlation_id,
            error_class=error_class,
            root_cause=f"Unclassified {error_class}: {str(error)[:200]}",
            classification="transient",  # Assume transient until proven otherwise
            severity=DiagnosticSeverity.MEDIUM,
            recommended_actions=[RemediationAction.RETRY, RemediationAction.ESCALATE_TO_USER],
            context_notes="Low-confidence heuristic fallback; LLM classification recommended",
            confidence=0.4,
        )

    async def _llm_classify(self, error: Exception, correlation_id: str,
                            agent_role: str, context: dict[str, Any] | None) -> Diagnosis:
        """LLM-assisted diagnosis for ambiguous cases. Uses Ollama only."""
        try:
            from app.services.ai.ollama import ollama_client, check_ollama
            if not check_ollama():
                # Can't even reach Ollama; fall back to heuristic
                return self._heuristic_classify(error, correlation_id, agent_role) or Diagnosis(
                    correlation_id=correlation_id,
                    error_class=type(error).__name__,
                    root_cause=str(error)[:300],
                    classification="transient",
                    severity=DiagnosticSeverity.MEDIUM,
                    recommended_actions=[RemediationAction.RETRY, RemediationAction.ESCALATE_TO_USER],
                    context_notes="Ollama unavailable for LLM diagnosis; heuristic fallback",
                    confidence=0.3,
                )

            context_summary = ""
            if context:
                context_summary = json.dumps({
                    k: str(v)[:200] for k, v in context.items()
                }, indent=2)

            prompt = f"""Classify this error from the {agent_role} agent in a multi-agent research authoring pipeline.

Error type: {type(error).__name__}
Error message: {str(error)[:500]}
Agent role: {agent_role}

Context: {context_summary[:1000] if context_summary else 'None'}

Classify as JSON:
{{"root_cause": "brief explanation", "classification": "transient|structural|environmental|quality", "recommended_actions": ["retry", "json_repair", "switch_provider", "simplify_prompt", "reduce_input", "increase_timeout", "inject_feedback", "escalate_to_user"], "confidence": 0.0-1.0}}"""

            result = ollama_client.complete(
                messages=[{"role": "user", "content": prompt}],
                system="You are an error classifier. Respond with only valid JSON.",
                model=settings.raptor_ollama_model,
                max_tokens=512,
                temperature=0.0,
                agent_role="diagnostic",
                operation="classify_error",
            )

            content = result["content"]
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(content[start:end])
                return Diagnosis(
                    correlation_id=correlation_id,
                    error_class=type(error).__name__,
                    root_cause=parsed.get("root_cause", str(error)[:200]),
                    classification=parsed.get("classification", "transient"),
                    severity=self._classify_severity(parsed.get("classification", "transient")),
                    recommended_actions=parsed.get("recommended_actions", [RemediationAction.RETRY]),
                    context_notes="LLM-classified via Ollama",
                    confidence=parsed.get("confidence", 0.6),
                )
        except Exception as e:
            logger.warning("[diagnostic] LLM classification failed: %s", e)

        # Final fallback
        return Diagnosis(
            correlation_id=correlation_id,
            error_class=type(error).__name__,
            root_cause=str(error)[:300],
            classification="transient",
            severity=DiagnosticSeverity.MEDIUM,
            recommended_actions=[RemediationAction.RETRY, RemediationAction.ESCALATE_TO_USER],
            context_notes="All classification methods failed; defaulting to retry + escalate",
            confidence=0.2,
        )

    def _classify_severity(self, classification: str) -> str:
        """Map classification to default severity."""
        return {
            "transient": DiagnosticSeverity.MEDIUM,
            "structural": DiagnosticSeverity.HIGH,
            "environmental": DiagnosticSeverity.HIGH,
            "quality": DiagnosticSeverity.MEDIUM,
        }.get(classification, DiagnosticSeverity.MEDIUM)


# Singleton
diagnostic_agent = DiagnosticAgent()
