"""ARQ Worker configuration and lifecycle hooks."""

from arq.cron import cron

from agents.analytics.queue import process_analytics_event
from agents.brain.worker import cron_process_batches, run_brain_pipeline
from agents.campaign_execution.queue import send_email_job
from agents.decision_engine.queue import evaluate_recipient_job, generate_followup_job
from core.database.engine import async_session_factory
from core.llm import get_llm_provider
from core.logger import get_logger
from core.queue.client import get_redis_settings

log = get_logger(__name__)


async def startup(ctx: dict) -> None:
    """
    Hook executed when the ARQ worker starts.
    Initializes database sessions and LLM providers and attaches them to the context.
    """
    log.info("Starting up ARQ worker...")

    # Provide the session factory
    ctx["db_session_factory"] = async_session_factory

    # Initialize LLM Provider
    ctx["llm_provider"] = get_llm_provider()

    # Register EventBus subscribers for decision evaluation
    from core.event_bus import event_bus
    from agents.decision_engine.queue import on_analytics_event

    for event_name in [
        "email_sent",
        "email_delivered",
        "email_opened",
        "email_clicked",
        "email_spam",
        "email_replied",
        "email_bounced"
    ]:
        event_bus.subscribe(event_name, on_analytics_event)

    log.info("ARQ worker startup complete.")


async def shutdown(ctx: dict) -> None:
    """
    Hook executed when the ARQ worker shuts down.
    """
    log.info("Shutting down ARQ worker...")
    log.info("ARQ worker shutdown complete.")


class WorkerSettings:
    """
    ARQ settings class. The worker process looks for this class to configure itself.
    """
    functions = [
        run_brain_pipeline,
        send_email_job,
        process_analytics_event,
        evaluate_recipient_job,
        generate_followup_job,
    ]
    cron_jobs = [
        # Run the brain batch processor every minute
        cron(cron_process_batches, minute={0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59}),
    ]

    on_startup = startup
    on_shutdown = shutdown

    redis_settings = get_redis_settings()

    # Queue configuration
    max_jobs = 10
    job_timeout = 300 # 5 minutes max per job

    # Let arq handle exceptions gracefully
    allow_abort_jobs = True
