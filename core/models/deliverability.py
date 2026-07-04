"""Deliverability models for domain and email account tracking."""

from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import AbstractModel


class DomainHealth(AbstractModel):
    """
    Tracks DNS records and overall deliverability health for sending domains.
    """
    __tablename__ = "domain_health"

    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    
    # DNS configuration status
    spf_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dkim_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dmarc_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Deliverability metrics
    bounce_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    spam_complaint_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reputation_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    
    # Check tracking
    last_checked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    @property
    def is_healthy(self) -> bool:
        """Returns True if the domain is fully authenticated and has good reputation."""
        return (
            self.spf_valid 
            and self.dkim_valid 
            and self.dmarc_valid 
            and not self.is_blacklisted
            and self.reputation_score > 80
            and self.bounce_rate < 5.0
            and self.spam_complaint_rate < 0.1
        )


class EmailAccountWarmup(AbstractModel):
    """
    Tracks the warmup status and daily sending limits of specific email accounts.
    """
    __tablename__ = "email_account_warmups"

    email_address: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    
    # Warmup status
    is_warming_up: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    warmup_day: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Limits
    current_daily_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_daily_limit: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    
    # Metrics
    emails_sent_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_sent_date: Mapped[datetime | None] = mapped_column(nullable=True)
