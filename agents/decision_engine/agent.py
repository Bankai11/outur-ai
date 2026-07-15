"""Orchestration Agent acting as the facade for the Decision Engine."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from agents.decision_engine.evaluation import DecisionEvaluator
from agents.decision_engine.models import DecisionResult
from agents.decision_engine.planner import ActionPlanner
from agents.decision_engine.repository import DecisionRepository

logger = logging.getLogger(__name__)


class DecisionEngineAgent:
    """Facade for the Autonomous Decision Engine."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = DecisionRepository(db)
        self.evaluator = DecisionEvaluator()
        self.planner = ActionPlanner(db)

    async def evaluate_contact(self, campaign_id: UUID, contact_id: UUID) -> DecisionResult:
        """Run the complete observe-evaluate-plan lifecycle for a contact."""
        # 1. Observe (Context gathering)
        context = await self.repo.get_evaluation_context(campaign_id, contact_id)

        # 2. Evaluate (Hybrid rules + AI)
        decision = await self.evaluator.evaluate_context(context)

        # 3. Plan & Schedule (State transitions and job queuing)
        await self.planner.execute_plan(decision)

        return decision
