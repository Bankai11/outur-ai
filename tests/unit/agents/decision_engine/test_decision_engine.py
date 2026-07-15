"""Unit tests for the Autonomous Decision Engine."""

from __future__ import annotations
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from agents.decision_engine.models import EvaluationContext, DecisionResult
from agents.decision_engine.rules import CampaignStateMachine, RuleEvaluator, StateTransitionError
from agents.decision_engine.planner import ActionPlanner, ACTION_STATE_MAP

def test_state_machine_valid_transitions():
    """Verify that allowed state transitions pass validation."""
    CampaignStateMachine.validate_transition("CREATED", "DISCOVERING")
    CampaignStateMachine.validate_transition("RUNNING", "WAITING")
    CampaignStateMachine.validate_transition("WAITING", "FOLLOWUP_PENDING")
    CampaignStateMachine.validate_transition("FOLLOWUP_PENDING", "FOLLOWUP_SENT")
    CampaignStateMachine.validate_transition("FOLLOWUP_SENT", "REPLIED")
    CampaignStateMachine.validate_transition("REPLIED", "MEETING_BOOKED")
    CampaignStateMachine.validate_transition("MEETING_BOOKED", "COMPLETED")


def test_state_machine_invalid_transitions():
    """Verify that forbidden transitions raise StateTransitionError."""
    with pytest.raises(StateTransitionError):
        CampaignStateMachine.validate_transition("COMPLETED", "CREATED")
        
    with pytest.raises(StateTransitionError):
        CampaignStateMachine.validate_transition("REPLIED", "RUNNING")
        
    with pytest.raises(StateTransitionError):
        CampaignStateMachine.validate_transition("FAILED", "WAITING")


def test_rule_evaluator_meeting_booked():
    """Verify meeting booked triggers MARK_SUCCESS action."""
    ctx = EvaluationContext(
        campaign_id=uuid4(),
        contact_id=uuid4(),
        current_state="WAITING",
        recipient_activity={"meeting_booked": True}
    )
    evaluator = RuleEvaluator()
    res = evaluator.evaluate(ctx)
    assert res is not None
    assert res.recommended_action == "MARK_SUCCESS"
    assert res.confidence == 1.0


def test_rule_evaluator_bounce():
    """Verify email bounce triggers MARK_FAILED action."""
    ctx = EvaluationContext(
        campaign_id=uuid4(),
        contact_id=uuid4(),
        current_state="WAITING",
        recipient_activity={"bounced_at": datetime.now().isoformat()}
    )
    evaluator = RuleEvaluator()
    res = evaluator.evaluate(ctx)
    assert res is not None
    assert res.recommended_action == "MARK_FAILED"
    assert res.rule_triggered == "BounceRule"


def test_rule_evaluator_max_followups():
    """Verify exceeding max followups triggers MARK_FAILED."""
    ctx = EvaluationContext(
        campaign_id=uuid4(),
        contact_id=uuid4(),
        current_state="WAITING",
        previous_emails_count=3 # Limit is 3
    )
    evaluator = RuleEvaluator(config={"max_followups": 3})
    res = evaluator.evaluate(ctx)
    assert res is not None
    assert res.recommended_action == "MARK_FAILED"
    assert res.rule_triggered == "MaxFollowupsExceededRule"


def test_rule_evaluator_followup_needed():
    """Verify followup is triggered when delay days are met."""
    ctx = EvaluationContext(
        campaign_id=uuid4(),
        contact_id=uuid4(),
        current_state="WAITING",
        days_since_last_interaction=4.5,
        previous_emails_count=1
    )
    evaluator = RuleEvaluator(config={"followup_delay_days": 3})
    res = evaluator.evaluate(ctx)
    assert res is not None
    assert res.recommended_action == "SEND_FOLLOWUP"


def test_rule_evaluator_wait():
    """Verify wait is recommended when delay days are not met."""
    ctx = EvaluationContext(
        campaign_id=uuid4(),
        contact_id=uuid4(),
        current_state="WAITING",
        days_since_last_interaction=1.5,
        previous_emails_count=1
    )
    evaluator = RuleEvaluator(config={"followup_delay_days": 3})
    res = evaluator.evaluate(ctx)
    assert res is not None
    assert res.recommended_action == "WAIT"
