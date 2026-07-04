"""AI Sequence Optimizer to learn optimal wait times and sequence steps."""

from core.logger import get_logger

log = get_logger(__name__)


class SequenceOptimizer:
    """
    Analyzes historical campaign sequence performance and determines
    the optimal wait times between touches based on industry and context.
    """

    def __init__(self, llm_provider):
        self.llm = llm_provider

    async def get_optimal_wait_days(self, industry: str, step_index: int) -> int:
        """
        Calculates the optimal wait days before the next sequence step.
        """
        log.info(f"Optimizing wait time for {industry} at step {step_index}")
        
        # In a real implementation, this would query the ABTestExperiment
        # and CampaignMemory tables to calculate average reply rates per wait day.
        # Here we simulate the logic:
        
        base_wait = 2 if step_index == 1 else 3
        
        industry = industry.lower() if industry else ""
        
        if "tech" in industry or "saas" in industry:
            # Tech moves fast, shorter waits
            return base_wait
        elif "healthcare" in industry or "medical" in industry:
            # Healthcare moves slower, longer waits
            return base_wait + 3
        elif "finance" in industry or "bank" in industry:
            return base_wait + 2
            
        return base_wait + 1

    async def generate_sequence_steps(self, profile: dict) -> list[dict]:
        """
        Generate a customized sequence strategy for a specific prospect.
        """
        # A basic default sequence: Email -> Wait -> Email -> LinkedIn -> Wait -> Email
        return [
            {"step_order": 1, "channel": "email"},
            {"step_order": 2, "channel": "wait", "wait_days": await self.get_optimal_wait_days(profile.get("industry", ""), 1)},
            {"step_order": 3, "channel": "email"},
            {"step_order": 4, "channel": "linkedin"},
            {"step_order": 5, "channel": "wait", "wait_days": await self.get_optimal_wait_days(profile.get("industry", ""), 4)},
            {"step_order": 6, "channel": "email"},
        ]
