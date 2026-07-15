"""Deterministic rules and State Machine validation for the Decision Engine."""

from __future__ import annotations

import logging
from typing import Any

from agents.decision_engine.models import DecisionResult, EvaluationContext

logger = logging.getLogger(__name__)


class StateTransitionError(ValueError):
    """Raised when an invalid state transition is attempted."""

    pass


class CampaignStateMachine:
    """Formal campaign and recipient state machine validating all transitions."""

    VALID_TRANSITIONS: dict[str, set[str]] = {
        "CREATED": {"DISCOVERING", "CANCELLED"},
        "DISCOVERING": {"ENRICHING", "FAILED", "CANCELLED"},
        "ENRICHING": {"SCORING", "FAILED", "CANCELLED"},
        "SCORING": {"RESEARCHING", "FAILED", "CANCELLED"},
        "RESEARCHING": {"GENERATING", "FAILED", "CANCELLED"},
        "GENERATING": {"READY", "FAILED", "CANCELLED"},
        "READY": {"QUEUED", "CANCELLED"},
        "QUEUED": {"RUNNING", "CANCELLED"},
        "RUNNING": {
            "WAITING",
            "FOLLOWUP_PENDING",
            "REPLIED",
            "MEETING_BOOKED",
            "COMPLETED",
            "FAILED",
            "CANCELLED",
        },
        "WAITING": {
            "FOLLOWUP_PENDING",
            "REPLIED",
            "MEETING_BOOKED",
            "COMPLETED",
            "FAILED",
            "CANCELLED",
        },
        "FOLLOWUP_PENDING": {"FOLLOWUP_SENT", "CANCELLED"},
        "FOLLOWUP_SENT": {
            "WAITING",
            "REPLIED",
            "MEETING_BOOKED",
            "COMPLETED",
            "FAILED",
            "CANCELLED",
        },
        "REPLIED": {"MEETING_BOOKED", "COMPLETED", "FAILED", "CANCELLED"},
        "MEETING_BOOKED": {"COMPLETED"},
        "COMPLETED": set(),
        "FAILED": set(),
        "CANCELLED": set(),
    }

    @classmethod
    def validate_transition(cls, from_state: str, to_state: str) -> None:
        """Validate if transition from one state to another is allowed."""
        from_state = from_state.upper()
        to_state = to_state.upper()

        if from_state not in cls.VALID_TRANSITIONS:
            raise StateTransitionError(f"Origin state '{from_state}' is invalid.")

        if to_state not in cls.VALID_TRANSITIONS[from_state] and from_state != to_state:
            raise StateTransitionError(f"Illegal state transition: {from_state} -> {to_state}.")


class RuleEvaluator:
    """Evaluates deterministic business rules against context."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.max_followups = self.config.get("max_followups", 3)
        self.followup_delay_days = self.config.get("followup_delay_days", 3)

    def evaluate(self, ctx: EvaluationContext) -> DecisionResult | None:
        """
        Evaluate context against deterministic rules.
        Returns a DecisionResult if a rule triggers with high confidence (1.0),
        otherwise returns None.
        """
        # Rule 1: Meeting Booked
        if ctx.current_state == "MEETING_BOOKED" or ctx.recipient_activity.get("meeting_booked"):
            return DecisionResult(
                campaign_id=ctx.campaign_id,
                recipient_id=ctx.contact_id,
                recommended_action="MARK_SUCCESS",
                reason="Meeting booked by recipient.",
                confidence=1.0,
                rule_triggered="MeetingBookedRule",
                priority="high",
            )

        # Rule 2: Reply Received
        if ctx.current_state == "REPLIED" or ctx.recipient_activity.get("replied_at") is not None:
            return DecisionResult(
                campaign_id=ctx.campaign_id,
                recipient_id=ctx.contact_id,
                recommended_action="STOP_CAMPAIGN",
                reason="Recipient replied to outreach.",
                confidence=1.0,
                rule_triggered="ReplyReceivedRule",
                priority="high",
            )

        # Rule 3: Bounce Detected
        if ctx.recipient_activity.get("bounced_at") is not None:
            return DecisionResult(
                campaign_id=ctx.campaign_id,
                recipient_id=ctx.contact_id,
                recommended_action="MARK_FAILED",
                reason="Email delivery bounced.",
                confidence=1.0,
                rule_triggered="BounceRule",
                priority="high",
            )

        # Rule 4: Maximum Follow-ups reached
        if ctx.previous_emails_count >= self.max_followups:
            return DecisionResult(
                campaign_id=ctx.campaign_id,
                recipient_id=ctx.contact_id,
                recommended_action="MARK_FAILED",
                reason=f"Reached maximum followup limit of {self.max_followups}.",
                confidence=1.0,
                rule_triggered="MaxFollowupsExceededRule",
                priority="medium",
            )

        # Rule 5: Send Follow-up
        if ctx.current_state in ("RUNNING", "WAITING", "FOLLOWUP_SENT"):
            if ctx.days_since_last_interaction >= self.followup_delay_days:
                reason_str = (
                    f"No response received after {ctx.days_since_last_interaction:.1f} days."
                )
                return DecisionResult(
                    campaign_id=ctx.campaign_id,
                    recipient_id=ctx.contact_id,
                    recommended_action="SEND_FOLLOWUP",
                    reason=reason_str,
                    confidence=1.0,
                    rule_triggered="FollowupRequiredRule",
                    priority="medium",
                )
            else:
                reason_str = (
                    f"Awaiting response (elapsed: {ctx.days_since_last_interaction:.1f}/"
                    f"{self.followup_delay_days} days)."
                )
                return DecisionResult(
                    campaign_id=ctx.campaign_id,
                    recipient_id=ctx.contact_id,
                    recommended_action="WAIT",
                    reason=reason_str,
                    confidence=1.0,
                    rule_triggered="WaitPeriodRule",
                    priority="low",
                )

        return None
