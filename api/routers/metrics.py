"""FastAPI router for system-wide health and operational metrics."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session
from core.models.analytics import ProviderEvent
from core.models.execution import CampaignDelivery, DeliveryAttempt
from core.queue.client import get_redis_pool

router = APIRouter()

@router.get("", status_code=status.HTTP_200_OK)
async def get_system_metrics(
    session: AsyncSession = Depends(get_session)  # noqa: B008
) -> dict[str, Any]:
    """
    Retrieve aggregated operational metrics.
    Gathers Redis queue depth, delivery stats, webhook counts, and latency metrics.
    """
    metrics: dict[str, Any] = {}

    # 1. Redis / ARQ Queue Depth
    queue_depth = 0
    try:
        redis_pool = await get_redis_pool()
        # Scan for queued jobs (arq typically keys them as arq:queue)
        queue_keys = await redis_pool.keys("arq:queue*")
        # Sum of job lists
        for k in queue_keys:
            queue_depth += await redis_pool.llen(k)
    except Exception:
        queue_depth = -1 # Unavailable

    metrics["queue"] = {
        "queue_depth": queue_depth
    }

    # 2. Database Delivery metrics
    deliveries_stmt = select(
        CampaignDelivery.status,
        func.count(CampaignDelivery.id)
    ).group_by(CampaignDelivery.status)

    delivery_res = await session.execute(deliveries_stmt)
    delivery_stats = dict(delivery_res.all())

    # 3. Latency and Retries
    latency_stmt = select(
        func.avg(DeliveryAttempt.latency_ms),
        func.count(DeliveryAttempt.id)
    )
    latency_res = await session.execute(latency_stmt)
    avg_latency, total_attempts = latency_res.first() or (0.0, 0)

    # 4. Webhook Ingest stats
    webhooks_stmt = select(
        ProviderEvent.provider_name,
        func.count(ProviderEvent.id)
    ).group_by(ProviderEvent.provider_name)
    webhook_res = await session.execute(webhooks_stmt)
    webhook_stats = dict(webhook_res.all())

    metrics["deliveries"] = {
        "statuses": delivery_stats,
        "total_attempts": total_attempts,
        "avg_latency_ms": round(float(avg_latency or 0.0), 2)
    }

    metrics["webhooks"] = {
        "ingested_by_provider": webhook_stats
    }

    return metrics
