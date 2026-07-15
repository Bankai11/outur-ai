"""Action Planner executing transitions and planning scheduler outcomes."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.decision_engine.models import DecisionResult
from agents.decision_engine.rules import CampaignStateMachine
from agents.decision_engine.scheduler import DecisionScheduler
from core.models.decision import DecisionHistory, RecipientLifecycle

logger = logging.getLogger(__name__)

# Map of action to next state
ACTION_STATE_MAP = {
    "WAIT": "WAITING",
    "SEND_FOLLOWUP": "FOLLOWUP_PENDING",
    "CHANGE_SUBJECT": "FOLLOWUP_PENDING",
    "CHANGE_TONE": "FOLLOWUP_PENDING",
    "SHORTEN_EMAIL": "FOLLOWUP_PENDING",
    "GENERATE_NEW_EMAIL": "FOLLOWUP_PENDING",
    "ESCALATE_TO_HUMAN": "WAITING",
    "STOP_CAMPAIGN": "COMPLETED",
    "MARK_SUCCESS": "MEETING_BOOKED",
    "MARK_FAILED": "FAILED",
}


class ActionPlanner:
    """Translates DecisionResult into state machine updates and scheduler tasks."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.scheduler = DecisionScheduler()

    async def execute_plan(self, decision: DecisionResult) -> None:
        """Apply state transition, save audit log, and schedule downstream actions."""
        # 1. Fetch lifecycle
        result = await self.db.execute(
            select(RecipientLifecycle).where(
                RecipientLifecycle.contact_id == decision.recipient_id,
                RecipientLifecycle.campaign_id == decision.campaign_id,
            )
        )
        lifecycle = result.scalars().first()

        if not lifecycle:
            lifecycle = RecipientLifecycle(
                contact_id=decision.recipient_id, campaign_id=decision.campaign_id, state="CREATED"
            )
            self.db.add(lifecycle)
            await self.db.flush()

        # 2. State Machine check
        old_state = lifecycle.state
        new_state = ACTION_STATE_MAP.get(decision.recommended_action, old_state)

        try:
            CampaignStateMachine.validate_transition(old_state, new_state)
            lifecycle.state = new_state
            lifecycle.state_entered_at = datetime.now(UTC)
        except Exception as e:
            logger.error(
                f"State transition error {old_state} -> {new_state} "
                f"for contact {decision.recipient_id}: {e}"
            )
            return

        # 3. Handle scheduling / queueing side effects
        if decision.recommended_action == "WAIT":
            # Set next evaluation to 3 days out
            lifecycle.next_evaluation_at = datetime.now(UTC) + timedelta(days=3)

        elif decision.recommended_action in (
            "SEND_FOLLOWUP",
            "CHANGE_SUBJECT",
            "CHANGE_TONE",
            "SHORTEN_EMAIL",
            "GENERATE_NEW_EMAIL",
        ):
            lifecycle.next_evaluation_at = None  # Awaiting delivery event now

            # Queue follow-up generation job
            await self.scheduler.schedule_followup_generation(
                campaign_id=decision.campaign_id,
                contact_id=decision.recipient_id,
                action_type=decision.recommended_action,
            )

        elif decision.recommended_action in ("STOP_CAMPAIGN", "MARK_SUCCESS", "MARK_FAILED"):
            lifecycle.next_evaluation_at = None

        # 4. Save to DecisionHistory
        history = DecisionHistory(
            recipient_lifecycle_id=lifecycle.id,
            inputs=decision.metadata.get("inputs", {}),
            decision=decision.model_dump(exclude={"metadata"}),
            confidence=decision.confidence,
            reason=decision.reason,
            execution_status="success",
            execution_outcome=f"State transitioned from {old_state} to {new_state}",
            llm_version=decision.metadata.get("llm_version"),
            prompt_version=decision.metadata.get("prompt_version"),
            rule_version=decision.metadata.get("rule_version"),
        )
        self.db.add(history)
        await self.db.commit()

        logger.info(
            f"Successfully updated lifecycle state to {new_state} "
            f"for contact {decision.recipient_id} in campaign {decision.campaign_id}"
        )
