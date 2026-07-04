"""Models for A/B testing and sequence optimization."""

from __future__ import annotations

import uuid
from sqlalchemy import String, JSON, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import AbstractModel


class ABTestExperiment(AbstractModel):
    """
    Tracks variations and outcomes for automated A/B testing
    across subjects, CTAs, lengths, and tones.
    """
    __tablename__ = "ab_test_experiments"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_metric: Mapped[str] = mapped_column(String(50), nullable=False) # open_rate, reply_rate, positive_reply_rate
    
    # Define the variants (e.g. {"A": {"tone": "casual"}, "B": {"tone": "professional"}})
    variants: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Track assignments and results
    # e.g. {"A": {"sent": 100, "replies": 10}, "B": {"sent": 100, "replies": 15}}
    results: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    status: Mapped[str] = mapped_column(String(50), default="running", nullable=False) # running, concluded
    winning_variant: Mapped[str | None] = mapped_column(String(50), nullable=True)
