"""Background worker tasks for the AI Sales Brain."""

from typing import Any
from core.logger import get_logger
from agents.brain.orchestrator import SalesBrainOrchestrator

log = get_logger(__name__)


async def run_brain_pipeline(ctx: dict, contact_id: str) -> None:
    """
    ARQ Task to run a single contact through the AI Sales Brain pipeline.
    """
    db_session_factory = ctx["db_session_factory"]
    llm_provider = ctx["llm_provider"]
    
    orchestrator = SalesBrainOrchestrator(llm_provider)
    
    # In a real implementation:
    # async with db_session_factory() as session:
    #     await orchestrator.run_pipeline_for_contact(contact_id, session)
    
    log.info(f"Running AI Sales Brain for contact: {contact_id}")
    await orchestrator.run_pipeline_for_contact(contact_id, session=None)


async def cron_process_batches(ctx: dict) -> None:
    """
    ARQ Cron job that periodically queries the DB for contacts needing attention
    and enqueues `run_brain_pipeline` jobs for each of them.
    """
    log.info("Cron: Checking for contacts that need brain processing...")
    
    # In a real implementation:
    # db_session_factory = ctx["db_session_factory"]
    # redis = ctx["redis"]
    # async with db_session_factory() as session:
    #     contacts = await get_pending_contacts(session)
    #     for c in contacts:
    #         await redis.enqueue_job("run_brain_pipeline", str(c.id))
    
    # Simulate finding one contact
    redis = ctx["redis"]
    simulated_contact_id = "123e4567-e89b-12d3-a456-426614174000"
    log.info(f"Enqueuing brain pipeline for contact: {simulated_contact_id}")
    await redis.enqueue_job("run_brain_pipeline", simulated_contact_id)
