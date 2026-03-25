"""Remediation Engine: executes fix strategies based on diagnostic results.

Dispatches to strategy implementations for each RemediationAction type.
Does NOT mutate global state; all fixes are scoped to the current retry.
"""

import asyncio
import json
import logging
import re
import time
from typing import Any

from app.core.config import settings
from app.models.constants import RemediationAction
from app.models.diagnostic import Diagnosis, RemediationResult
from app.models.envelope import ArtifactEnvelope

logger = logging.getLogger(__name__)


class RemediationEngine:
    """Executes remediation strategies. Max attempts controlled by caller."""

    async def attempt(
        self,
        diagnosis: Diagnosis,
        agent: Any,
        project: Any,
        venue: Any,
        attempt: int,
        raw_output: str = "",
    ) -> RemediationResult:
        """Try the next recommended remediation action."""
        if attempt >= len(diagnosis.recommended_actions):
            return RemediationResult(
                success=False,
                action_taken=RemediationAction.ESCALATE_TO_USER,
                attempt_number=attempt,
                notes="All recommended actions exhausted",
            )

        action = diagnosis.recommended_actions[attempt]
        start = time.monotonic()

        logger.info("[remediation] Attempt %d: %s for %s", attempt + 1, action, diagnosis.error_class)

        try:
            if action == RemediationAction.RETRY:
                result = await self._retry(agent, project, venue)
            elif action == RemediationAction.RETRY_WITH_BACKOFF:
                result = await self._retry_with_backoff(agent, project, venue, attempt)
            elif action == RemediationAction.JSON_REPAIR:
                result = self._json_repair(raw_output, agent, project)
            elif action == RemediationAction.SWITCH_PROVIDER:
                result = await self._switch_provider(agent, project, venue)
            elif action == RemediationAction.SIMPLIFY_PROMPT:
                result = await self._simplify_prompt(agent, project, venue)
            elif action == RemediationAction.REDUCE_INPUT:
                result = await self._reduce_input(agent, project, venue)
            elif action == RemediationAction.INCREASE_TIMEOUT:
                result = await self._increase_timeout(agent, project, venue)
            elif action == RemediationAction.INJECT_FEEDBACK:
                result = await self._inject_feedback(agent, project, venue)
            else:
                result = RemediationResult(
                    success=False,
                    action_taken=action,
                    attempt_number=attempt,
                    notes=f"Unknown action: {action}",
                )
        except Exception as e:
            result = RemediationResult(
                success=False,
                action_taken=action,
                attempt_number=attempt,
                notes=f"Remediation failed: {e}",
            )

        duration = int((time.monotonic() - start) * 1000)
        result.duration_ms = duration
        result.attempt_number = attempt

        if result.success:
            logger.info("[remediation] Success: %s resolved the issue in %dms", action, duration)
        else:
            logger.warning("[remediation] Failed: %s did not resolve the issue", action)

        return result

    async def _retry(self, agent: Any, project: Any, venue: Any) -> RemediationResult:
        """Simple retry: re-execute the agent unchanged."""
        envelope = await agent.execute(project, venue)
        return RemediationResult(
            success=True,
            action_taken=RemediationAction.RETRY,
            attempt_number=0,
            envelope=envelope.model_dump() if hasattr(envelope, "model_dump") else None,
            notes="Retry succeeded",
        )

    async def _retry_with_backoff(self, agent: Any, project: Any, venue: Any, attempt: int) -> RemediationResult:
        """Retry with exponential backoff."""
        wait_s = min(2 ** attempt, 30)
        logger.info("[remediation] Waiting %ds before retry", wait_s)
        await asyncio.sleep(wait_s)
        return await self._retry(agent, project, venue)

    def _json_repair(self, raw_output: str, agent: Any, project: Any) -> RemediationResult:
        """Attempt to repair malformed JSON output."""
        if not raw_output:
            return RemediationResult(success=False, action_taken=RemediationAction.JSON_REPAIR,
                                    attempt_number=0, notes="No raw output to repair")

        repaired = raw_output

        # Fix 1: Remove trailing commas before closing braces/brackets
        repaired = re.sub(r',\s*([}\]])', r'\1', repaired)

        # Fix 2: Remove markdown code fences
        repaired = re.sub(r'^```(?:json)?\s*\n?', '', repaired, flags=re.MULTILINE)
        repaired = re.sub(r'\n?```\s*$', '', repaired, flags=re.MULTILINE)

        # Fix 3: Fix unescaped newlines in strings
        repaired = repaired.replace('\n', '\\n').replace('\\n\\n', '\\n')

        # Fix 4: Extract JSON block if embedded in prose
        start = repaired.find("{")
        end = repaired.rfind("}") + 1
        if start >= 0 and end > start:
            candidate = repaired[start:end]
            # Re-fix the extracted candidate (undo overzealous newline escaping)
            candidate = candidate.replace('\\n', '\n')
            candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
            try:
                parsed = json.loads(candidate)
                return RemediationResult(
                    success=True,
                    action_taken=RemediationAction.JSON_REPAIR,
                    attempt_number=0,
                    envelope={"payload": parsed, "_repaired": True},
                    notes=f"JSON repaired: extracted {len(candidate)} chars from position {start}",
                )
            except json.JSONDecodeError:
                pass

        return RemediationResult(success=False, action_taken=RemediationAction.JSON_REPAIR,
                                attempt_number=0, notes="JSON repair failed: could not extract valid JSON")

    async def _switch_provider(self, agent: Any, project: Any, venue: Any) -> RemediationResult:
        """Switch to alternate AI provider for this retry only."""
        from app.services.ai.ollama import ollama_client, check_ollama
        from app.services.ai.claude_cli import claude_cli_client, check_claude_cli
        from app.services.ai import router as ai_router

        current = ai_router.get_provider()

        if current == "claude-cli" and check_ollama():
            # Temporarily patch the agent's complete method to use Ollama
            logger.info("[remediation] Switching from claude-cli to ollama for retry")
            original_complete = agent.complete

            async def ollama_complete(**kwargs):
                return ollama_client.complete(**{k: v for k, v in kwargs.items() if k != "self"})

            agent.complete = ollama_complete
            try:
                envelope = await agent.execute(project, venue)
                return RemediationResult(
                    success=True, action_taken=RemediationAction.SWITCH_PROVIDER,
                    attempt_number=0, envelope=envelope.model_dump() if hasattr(envelope, "model_dump") else None,
                    notes="Switched to Ollama provider",
                )
            finally:
                agent.complete = original_complete

        elif current == "ollama" and check_claude_cli():
            logger.info("[remediation] Switching from ollama to claude-cli for retry")
            original_complete = agent.complete

            async def cli_complete(**kwargs):
                return claude_cli_client.complete(**{k: v for k, v in kwargs.items() if k != "self"})

            agent.complete = cli_complete
            try:
                envelope = await agent.execute(project, venue)
                return RemediationResult(
                    success=True, action_taken=RemediationAction.SWITCH_PROVIDER,
                    attempt_number=0, envelope=envelope.model_dump() if hasattr(envelope, "model_dump") else None,
                    notes="Switched to Claude CLI provider",
                )
            finally:
                agent.complete = original_complete

        return RemediationResult(success=False, action_taken=RemediationAction.SWITCH_PROVIDER,
                                attempt_number=0, notes="No alternate provider available")

    async def _simplify_prompt(self, agent: Any, project: Any, venue: Any) -> RemediationResult:
        """Retry with simplified prompt (less context)."""
        # Reduce author_context to first 200 chars
        original_context = project.author_context
        project.author_context = (project.author_context or "")[:200]
        try:
            envelope = await agent.execute(project, venue)
            return RemediationResult(
                success=True, action_taken=RemediationAction.SIMPLIFY_PROMPT,
                attempt_number=0, envelope=envelope.model_dump() if hasattr(envelope, "model_dump") else None,
                notes="Simplified prompt (truncated author context)",
            )
        finally:
            project.author_context = original_context

    async def _reduce_input(self, agent: Any, project: Any, venue: Any) -> RemediationResult:
        """Retry with reduced input size."""
        return await self._simplify_prompt(agent, project, venue)

    async def _increase_timeout(self, agent: Any, project: Any, venue: Any) -> RemediationResult:
        """Retry with increased timeout."""
        # The timeout is in the provider clients; for now just retry
        # (actual timeout increase would need provider-level config)
        return await self._retry(agent, project, venue)

    async def _inject_feedback(self, agent: Any, project: Any, venue: Any) -> RemediationResult:
        """Retry with reviewer feedback injected into the prompt."""
        from app.services import artifact_service
        from app.models.constants import ArtifactType

        review = artifact_service.get_latest_artifact(project.id, ArtifactType.REVIEW)
        if review and review.rejection_context:
            # Append feedback to author_context temporarily
            original = project.author_context
            feedback = "\n\nREVIEWER FEEDBACK: " + ", ".join(review.rejection_context.required_changes[:5])
            project.author_context = (project.author_context or "") + feedback
            try:
                envelope = await agent.execute(project, venue)
                return RemediationResult(
                    success=True, action_taken=RemediationAction.INJECT_FEEDBACK,
                    attempt_number=0, envelope=envelope.model_dump() if hasattr(envelope, "model_dump") else None,
                    notes="Injected reviewer feedback into prompt",
                )
            finally:
                project.author_context = original

        return RemediationResult(success=False, action_taken=RemediationAction.INJECT_FEEDBACK,
                                attempt_number=0, notes="No review feedback available to inject")


# Singleton
remediation_engine = RemediationEngine()
