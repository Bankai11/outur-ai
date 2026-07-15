"""Orchestrates hybrid rule-based and LLM-augmented reasoning."""

from __future__ import annotations

import logging
from typing import Any

from agents.decision_engine.llm import LLMReasoner
from agents.decision_engine.models import DecisionResult, EvaluationContext
from agents.decision_engine.rules import RuleEvaluator

logger = logging.getLogger(__name__)


class DecisionEvaluator:
    """Orchestrates hybrid rule-based and AI-augmented evaluations."""

    def __init__(self, rule_config: dict[str, Any] | None = None) -> None:
        self.rule_evaluator = RuleEvaluator(rule_config)
        self.llm_reasoner = LLMReasoner()

    async def evaluate_context(self, ctx: EvaluationContext) -> DecisionResult:
        """
        Evaluate context against deterministic rules first.
        Falls back to LLM reasoning if rules do not produce a high-confidence recommendation.
        """
        logger.info(
            f"Evaluating recipient {ctx.contact_id} in campaign {ctx.campaign_id}. "
            f"State: {ctx.current_state}"
        )

        # 1. Evaluate deterministic rules
        rule_result = self.rule_evaluator.evaluate(ctx)

        if rule_result and rule_result.confidence >= 0.8:
            logger.info(
                f"Deterministic rule triggered: {rule_result.rule_triggered} "
                f"with confidence {rule_result.confidence}"
            )
            rule_result.metadata["inputs"] = ctx.model_dump()
            rule_result.metadata["rule_version"] = "1.0"
            return rule_result

        # 2. Hybrid fallback to LLM
        logger.info("Deterministic rules inconclusive. Invoking LLM reasoning fallback.")
        llm_result = await self.llm_reasoner.analyze(ctx)
        llm_result.metadata["inputs"] = ctx.model_dump()
        llm_result.metadata["llm_version"] = "gemini-3.5-flash"

        # Ensure correct IDs are attached
        llm_result.campaign_id = ctx.campaign_id
        llm_result.recipient_id = ctx.contact_id

        return llm_result
