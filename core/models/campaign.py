"""Campaign database model."""

from __future__ import annotations

from typing import Any
from sqlalchemy import String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import AbstractModel


class Campaign(AbstractModel):
    """
    Campaign metadata, targeting filters, and selection of companies and contacts.
    """

    __tablename__ = "campaigns"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    filters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    
    # Store list of selected company UUID strings
    selected_companies: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    
    # Store list of selected contact UUID strings
    selected_contacts: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
