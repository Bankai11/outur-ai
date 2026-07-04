"""
Models package.

Import all ORM models here so Alembic can discover them via ``Base.metadata``
when auto-generating migrations.

Example (add as you create models)::

    from core.models.company import Company        # noqa: F401
    from core.models.lead import Lead              # noqa: F401
    from core.models.campaign import Campaign      # noqa: F401
"""

from core.models.base import AbstractModel
from core.models.company import Company
from core.models.contact import Contact
from core.models.research_profile import ResearchProfile
from core.models.campaign import Campaign
from core.models.outreach_draft import OutreachDraft
from core.models.sequence import OutreachSequence, SequenceStep
from core.models.experiment import ABTestExperiment
from core.models.memory import CompanyMemory, ContactMemory, CampaignMemory, OrganizationMemory, ConversationMemory, IndustryMemory, MarketMemory
from core.models.deliverability import DomainHealth, EmailAccountWarmup

__all__ = [
    "AbstractModel",
    "Company",
    "Contact",
    "ResearchProfile",
    "Campaign",
    "OutreachDraft",
    "OutreachSequence",
    "SequenceStep",
    "ABTestExperiment",
    "CompanyMemory",
    "ContactMemory",
    "CampaignMemory",
    "OrganizationMemory",
    "ConversationMemory",
    "IndustryMemory",
    "MarketMemory",
    "DomainHealth",
    "EmailAccountWarmup",
]

