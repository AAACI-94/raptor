"""Pipeline orchestrator: the central nervous system of RAPTOR.

Manages stage transitions, rejection loops, revision counting, quality gates,
and coordinates agent execution with WebSocket broadcasting.
"""

import json
import logging
import uuid
from datetime import datetime, timezone

from app.core.config import settings
from app.core.database import get_db
from app.models.constants import (
    ProjectStatus, AgentRole, ArtifactType, ArtifactStatus,
    VALID_TRANSITIONS, STATUS_TO_AGENT,
)
from app.models.envelope import ArtifactEnvelope, ArtifactMetadata
from app.models.pipeline import PipelineStatus, StageTransition
from app.services import project_service, artifact_service, venue_service
from app.services.pipeline.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

# Maps pipeline status to the agent that should run
STAGE_AGENT_MAP = {
    ProjectStatus.RESEARCHING: "research_strategist",
    ProjectStatus.STRUCTURING: "structure_architect",
    ProjectStatus.DRAFTING: "domain_writer",
    ProjectStatus.ILLUSTRATING: "visual_architect",
    ProjectStatus.REVIEWING: "critical_reviewer",
    ProjectStatus.PRODUCING: "production_agent",
}

# Maps pipeline status to the artifact type it produces
STAGE_ARTIFACT_MAP = {
    ProjectStatus.RESEARCHING: ArtifactType.RESEARCH_PLAN,
    ProjectStatus.STRUCTURING: ArtifactType.OUTLINE,
    ProjectStatus.DRAFTING: ArtifactType.SECTION_DRAFT,
    ProjectStatus.ILLUSTRATING: ArtifactType.FIGURES,
    ProjectStatus.REVIEWING: ArtifactType.REVIEW,
    ProjectStatus.PRODUCING: ArtifactType.PRODUCTION_OUTPUT,
}

# Maps a "complete" status to the next "active" status
ADVANCE_MAP = {
    ProjectStatus.TOPIC_SELECTED: ProjectStatus.RESEARCHING,
    ProjectStatus.RESEARCH_COMPLETE: ProjectStatus.STRUCTURING,
    ProjectStatus.STRUCTURE_COMPLETE: ProjectStatus.DRAFTING,
    ProjectStatus.DRAFT_COMPLETE: ProjectStatus.ILLUSTRATING,
    ProjectStatus.ILLUSTRATION_COMPLETE: ProjectStatus.REVIEWING,
    ProjectStatus.REVIEW_PASSED: ProjectStatus.PRODUCING,
    ProjectStatus.PRODUCTION_COMPLETE: ProjectStatus.PUBLISHED,
}


class PipelineOrchestrator:
    """Orchestrates the multi-agent pipeline for a project."""

    def __init__(self):
        self._agents: dict[str, Any] = {}

    def register_agent(self, role: str, agent: Any) -> None:
        """Register an agent implementation."""
        self._agents[role] = agent
        logger.info("[pipeline] Registered agent: %s", role)

    async def start_pipeline(self, project_id: str) -> dict:
        """Start the pipeline from TOPIC_SELECTED."""
        project = project_service.get_project(project_id)

        if project.status != ProjectStatus.TOPIC_SELECTED:
            raise ValueError(f"Cannot start pipeline: project is in {project.status} state")

        if not project.venue_profile_id:
            raise ValueError("Cannot start pipeline: no venue profile selected")

        if not project.topic_description:
            raise ValueError("Cannot start pipeline: no topic description provided")

        # Transition to RESEARCHING
        self._transition(project_id, ProjectStatus.RESEARCHING)

        # Run the research agent
        result = await self._run_stage(project_id, ProjectStatus.RESEARCHING)
        return result

    async def advance_pipeline(self, project_id: str) -> dict:
        """Advance to the next pipeline stage."""
        project = project_service.get_project(project_id)

        next_status = ADVANCE_MAP.get(ProjectStatus(project.status))
        if next_status is None:
            raise ValueError(f"Cannot advance from {project.status}")

        self._transition(project_id, next_status)

        # If the next status is an active stage, run the agent
        if next_status in STAGE_AGENT_MAP:
            result = await self._run_stage(project_id, next_status)
            return result

        return {"status": next_status, "message": "Advanced to " + next_status}

    async def reject_stage(self, project_id: str, feedback: str, target_stage: str | None = None) -> dict:
        """Reject current stage output and send back for revision."""
        project = project_service.get_project(project_id)

        # Check revision limit
        cycles = project_service.increment_revision_cycles(project_id)
        if cycles > settings.raptor_max_revision_cycles:
            await ws_manager.broadcast(project_id, {
                "event": "escalation",
                "message": f"Maximum revision cycles ({settings.raptor_max_revision_cycles}) reached. Author intervention required.",
                "revision_cycles": cycles,
            })
            return {
                "status": "escalated",
                "message": "Maximum revision cycles reached",
                "revision_cycles": cycles,
            }

        # Determine target for revision
        if target_stage:
            target_status = ProjectStatus(target_stage)
        else:
            # Default: send back one stage
            current = ProjectStatus(project.status)
            revision_targets = VALID_TRANSITIONS.get(ProjectStatus.REVISION_REQUESTED, [])
            target_status = revision_targets[0] if revision_targets else ProjectStatus.DRAFTING

        self._transition(project_id, ProjectStatus.REVISION_REQUESTED, reason=feedback)
        self._transition(project_id, target_status)

        # Re-run the target stage
        result = await self._run_stage(project_id, target_status)
        return result

    async def override_stage(self, project_id: str, reason: str = "") -> dict:
        """Override rejection and force-advance."""
        project = project_service.get_project(project_id)
        logger.warning("[pipeline] Override on project %s: %s", project_id, reason)

        # Log the override
        self._log_decision(project_id, "pipeline", "override",
                          f"Author override: {reason}", confidence=1.0)

        # Force transition to REVIEW_PASSED or next logical state
        current = ProjectStatus(project.status)
        if current == ProjectStatus.REVIEWING or current == ProjectStatus.REVISION_REQUESTED:
            self._transition(project_id, ProjectStatus.REVIEW_PASSED)
        elif current in ADVANCE_MAP:
            next_status = ADVANCE_MAP[current]
            self._transition(project_id, next_status)

        return {"status": "overridden", "reason": reason}

    def get_pipeline_status(self, project_id: str) -> PipelineStatus:
        """Get current pipeline state."""
        project = project_service.get_project(project_id)
        artifacts = artifact_service.list_artifacts(project_id)

        current_agent = STAGE_AGENT_MAP.get(ProjectStatus(project.status))

        return PipelineStatus(
            project_id=project_id,
            status=project.status,
            revision_cycles=project.revision_cycles,
            max_revision_cycles=settings.raptor_max_revision_cycles,
            current_agent=current_agent,
            artifacts=artifacts,
        )

    async def _run_stage(self, project_id: str, status: ProjectStatus) -> dict:
        """Run the agent for a given stage."""
        agent_role = STAGE_AGENT_MAP.get(status)
        if not agent_role:
            return {"status": str(status), "message": "No agent for this stage"}

        agent = self._agents.get(agent_role)
        if not agent:
            logger.warning("[pipeline] No agent registered for %s, using stub", agent_role)
            return await self._run_stub(project_id, status, agent_role)

        project = project_service.get_project(project_id)
        venue = venue_service.get_venue(project.venue_profile_id) if project.venue_profile_id else None

        # Broadcast start
        await ws_manager.broadcast(project_id, {
            "event": "agent_started",
            "agent": agent_role,
            "stage": str(status),
        })

        try:
            # Execute the agent (with Sentinel protection if enabled)
            if settings.raptor_sentinel_enabled:
                from app.services.pipeline.sentinel import sentinel
                envelope = await sentinel.execute_with_protection(agent, project, venue, project_id)
            else:
                envelope = await agent.execute(project, venue)

            # Store the artifact
            artifact_service.store_artifact(envelope)

            # Auto-populate library metadata based on which stage just completed
            self._update_library_metadata(project_id, status, envelope)

            # Determine next status based on agent output
            if status == ProjectStatus.REVIEWING and envelope.rejection_context:
                # Critical Reviewer recommended revise/reject: trigger revision loop
                complete_status = ProjectStatus.REVISION_REQUESTED
                cycles = project_service.increment_revision_cycles(project_id)
                if cycles > settings.raptor_max_revision_cycles:
                    # Max revisions reached: escalate to author
                    await ws_manager.broadcast(project_id, {
                        "event": "escalation",
                        "message": f"Maximum revision cycles ({settings.raptor_max_revision_cycles}) reached after review rejection. Author intervention required.",
                        "revision_cycles": cycles,
                    })
                    self._transition(project_id, complete_status)
                    return {
                        "status": "escalated",
                        "agent": agent_role,
                        "artifact_id": envelope.artifact_id,
                        "revision_cycles": cycles,
                        "rejection": envelope.rejection_context.model_dump(),
                    }

                # Send back for revision
                target = envelope.rejection_context.target_for_revision
                self._transition(project_id, complete_status,
                                reason=f"Reviewer recommended revise (score: {envelope.quality_scores})")

                # Determine which stage to re-run
                revision_target = ProjectStatus.DRAFTING  # Default: re-draft
                if target == "structure_architect":
                    revision_target = ProjectStatus.STRUCTURING
                elif target == "research_strategist":
                    revision_target = ProjectStatus.RESEARCHING

                self._transition(project_id, revision_target)

                await ws_manager.broadcast(project_id, {
                    "event": "revision_requested",
                    "agent": agent_role,
                    "target": target,
                    "artifact_id": envelope.artifact_id,
                    "failed_criteria": envelope.rejection_context.failed_criteria,
                })

                # Re-run the target stage
                logger.info("[pipeline] Review rejected, re-running %s (cycle %d)", revision_target, cycles)
                return await self._run_stage(project_id, revision_target)
            else:
                complete_status = self._get_complete_status(status)
                if complete_status:
                    self._transition(project_id, complete_status)

            # Broadcast completion
            await ws_manager.broadcast(project_id, {
                "event": "agent_completed",
                "agent": agent_role,
                "artifact_id": envelope.artifact_id,
                "stage": str(status),
            })

            return {
                "status": str(complete_status or status),
                "agent": agent_role,
                "artifact_id": envelope.artifact_id,
            }

        except Exception as e:
            logger.error("[pipeline] Agent %s failed: %s", agent_role, e)
            await ws_manager.broadcast(project_id, {
                "event": "agent_error",
                "agent": agent_role,
                "error": str(e),
            })
            raise

    async def _run_stub(self, project_id: str, status: ProjectStatus, agent_role: str) -> dict:
        """Run a stub agent for stages without registered agents."""
        artifact_type = STAGE_ARTIFACT_MAP.get(status, ArtifactType.RESEARCH_PLAN)
        version = artifact_service.get_next_version(project_id, artifact_type, agent_role)

        envelope = ArtifactEnvelope(
            artifact_id=str(uuid.uuid4()),
            artifact_type=artifact_type,
            source_agent=agent_role,
            project_id=project_id,
            version=version,
            payload={"stub": True, "message": f"Stub output from {agent_role}"},
            metadata=ArtifactMetadata(model="stub", duration_ms=0),
            status=ArtifactStatus.SUBMITTED,
        )
        artifact_service.store_artifact(envelope)

        complete_status = self._get_complete_status(status)
        if complete_status:
            self._transition(project_id, complete_status)

        return {"status": str(complete_status or status), "agent": agent_role, "stub": True}

    def _transition(self, project_id: str, new_status: ProjectStatus, reason: str = "") -> None:
        """Transition a project to a new status."""
        project_service.update_project_status(project_id, new_status)
        self._log_decision(project_id, "pipeline", "transition",
                          f"Transitioned to {new_status}: {reason}" if reason else f"Transitioned to {new_status}",
                          confidence=1.0)
        logger.info("[pipeline] Project %s -> %s", project_id, new_status)

    def _get_complete_status(self, active_status: ProjectStatus) -> ProjectStatus | None:
        """Get the 'complete' status for an 'active' status."""
        mapping = {
            ProjectStatus.RESEARCHING: ProjectStatus.RESEARCH_COMPLETE,
            ProjectStatus.STRUCTURING: ProjectStatus.STRUCTURE_COMPLETE,
            ProjectStatus.DRAFTING: ProjectStatus.DRAFT_COMPLETE,
            ProjectStatus.ILLUSTRATING: ProjectStatus.ILLUSTRATION_COMPLETE,
            ProjectStatus.REVIEWING: ProjectStatus.REVIEW_PASSED,  # Default pass; Reviewer may override
            ProjectStatus.PRODUCING: ProjectStatus.PRODUCTION_COMPLETE,
        }
        return mapping.get(active_status)

    def _update_library_metadata(self, project_id: str, status: ProjectStatus, envelope: Any) -> None:
        """Auto-populate library metadata after each stage completes."""
        try:
            if status == ProjectStatus.RESEARCHING:
                # Auto-tag from research output
                project_service.auto_tag_from_research(project_id, envelope.payload)

            elif status == ProjectStatus.PRODUCING:
                # Extract abstract and update word/figure counts
                abstract = project_service.auto_extract_abstract(project_id, envelope.payload)
                word_count = envelope.payload.get("total_word_count", 0)
                project_service.update_library_metadata(
                    project_id,
                    word_count=word_count,
                )

            elif status == ProjectStatus.ILLUSTRATING:
                # Update figure count
                figures = envelope.payload.get("figures", [])
                project_service.update_library_metadata(
                    project_id,
                    figure_count=len(figures),
                )

            elif status == ProjectStatus.REVIEWING:
                # Update quality score from review
                scores = envelope.quality_scores
                if scores:
                    avg = sum(scores.values()) / len(scores)
                    project_service.update_library_metadata(
                        project_id,
                        quality_score=round(avg, 1),
                    )

                # Update cost
                try:
                    cost_row = get_db().execute(
                        "SELECT SUM(estimated_cost_usd) as total FROM token_usage WHERE project_id = ?",
                        (project_id,),
                    ).fetchone()
                    if cost_row and cost_row["total"]:
                        project_service.update_library_metadata(
                            project_id,
                            total_cost_usd=round(cost_row["total"], 4),
                        )
                except Exception:
                    pass

        except Exception as e:
            logger.warning("[pipeline] Failed to update library metadata: %s", e)

    def _log_decision(self, project_id: str, agent: str, decision_type: str,
                     rationale: str, confidence: float = 0.0) -> None:
        """Log a pipeline decision."""
        try:
            db = get_db()
            db.execute(
                """INSERT INTO decision_logs (id, project_id, agent, decision, rationale, confidence)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), project_id, agent, decision_type, rationale, confidence),
            )
            db.commit()
        except Exception as e:
            logger.warning("[pipeline] Failed to log decision: %s", e)


# Singleton
orchestrator = PipelineOrchestrator()


# Import is deferred to avoid circular imports
from typing import Any
