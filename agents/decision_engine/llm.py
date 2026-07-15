"""LLM Interface for AI-augmented reasoning in the Decision Engine."""

from __future__ import annotations

import json
import logging

from agents.decision_engine.models import DecisionResult, EvaluationContext
from core.llm import get_llm_provider

logger = logging.getLogger(__name__)

DECISION_LLM_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "recommended_action": {
            "type": "STRING",
            "description": (
                "Choice: WAIT, SEND_FOLLOWUP, CHANGE_SUBJECT, CHANGE_TONE, "
                "SHORTEN_EMAIL, GENERATE_NEW_EMAIL, ESCALATE_TO_HUMAN, "
                "STOP_CAMPAIGN, MARK_SUCCESS, MARK_FAILED"
            ),
        },
        "reason": {"type": "STRING", "description": "Justification for this recommended action."},
        "confidence": {"type": "NUMBER", "description": "Confidence level between 0.0 and 1.0."},
    },
    "required": ["recommended_action", "reason", "confidence"],
}


class LLMReasoner:
    """Uses LLM to perform deep analysis of context when rules do not give a definitive result."""

    def __init__(self, provider_name: str | None = None) -> None:
        self.provider_name = provider_name

    async def analyze(self, ctx: EvaluationContext) -> DecisionResult:
        """Call LLM provider to evaluate context and determine next best action."""
        llm = get_llm_provider()

        prompt = f"""
        Analyze the following business development campaign state and recipient
        interaction history to determine the next best action.

        Campaign ID: {ctx.campaign_id}
        Contact ID: {ctx.contact_id}
        Current State: {ctx.current_state}
        Opportunity Score: {ctx.opportunity_score}

        Recipient Activity:
        {json.dumps(ctx.recipient_activity, indent=2)}

        Email Events History:
        {json.dumps(ctx.email_events, indent=2)}

        Previous Emails Sent: {ctx.previous_emails_count}
        Days since last interaction: {ctx.days_since_last_interaction}
        Buying Signals: {json.dumps(ctx.buying_signals)}
        Company Context: {json.dumps(ctx.company_context)}

        Evaluate rules:
        - If the reply indicates interest, return MARK_SUCCESS.
        - If they ask to be unsubscribed or say "no interest", return STOP_CAMPAIGN or MARK_FAILED.
        - If they asked a pricing question, suggest ESCALATE_TO_HUMAN.
        - If they did not reply but opened the email multiple times,
          suggest SEND_FOLLOWUP or CHANGE_SUBJECT.
        - If they did not reply and did not open, suggest CHANGE_TONE or SHORTEN_EMAIL.

        Format your response as a JSON object matching the schema.
        """

        try:
            res_dict = await llm.generate_json(prompt, DECISION_LLM_SCHEMA)
            if res_dict:
                return DecisionResult(
                    campaign_id=ctx.campaign_id,
                    recipient_id=ctx.contact_id,
                    recommended_action=res_dict["recommended_action"],
                    reason=res_dict["reason"],
                    confidence=float(res_dict["confidence"]),
                    llm_used=True,
                    metadata={"provider": self.provider_name or "default"},
                )
        except Exception as e:
            logger.error(f"Error during LLM reasoning evaluation: {e}", exc_info=True)

        # Safe fallback decision if LLM fails
        return DecisionResult(
            campaign_id=ctx.campaign_id,
            recipient_id=ctx.contact_id,
            recommended_action="WAIT",
            reason="LLM evaluation failed; falling back to WAITING state.",
            confidence=0.5,
            llm_used=True,
            metadata={"error": "LLM failed"},
        )
