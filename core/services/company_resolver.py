"""
Shared company resolution service.

Single source of truth for resolving a ``Company`` ORM instance from
either an already-loaded object or a raw identifier (``str | uuid.UUID``).

Every agent that needs to work with a company should call
:meth:`resolve_company` instead of duplicating the UUID-parse → DB-lookup
→ NotFoundError pattern.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from core.models.company import Company
from core.utils.exceptions import NotFoundError

log = get_logger(__name__)


def _parse_uuid(value: str | uuid.UUID) -> uuid.UUID:
    """Parse a ``str`` into a ``uuid.UUID``, raising ``NotFoundError`` on failure.

    Parameters
    ----------
    value:
        A UUID string or an already-parsed ``uuid.UUID`` instance.

    Returns
    -------
    uuid.UUID
        The validated UUID.

    Raises
    ------
    NotFoundError
        If *value* is a ``str`` that cannot be parsed as a UUID.
    """
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise NotFoundError("Company", value) from exc


async def resolve_company(
    company_id: str | uuid.UUID | None,
    session: AsyncSession,
    *,
    company: Company | None = None,
) -> Company:
    """Resolve a ``Company`` record from an identifier or pre-loaded object.

    This is the **only** function agents should call to obtain a ``Company``
    instance.  It handles three cases in order of priority:

    1. An already-loaded ``Company`` object is passed via *company* — returned
       as-is (no DB round-trip).
    2. A *company_id* is provided — parsed to a UUID, looked up in the DB.
    3. Neither is provided, or the lookup fails — ``NotFoundError`` is raised.

    Parameters
    ----------
    company_id:
        A UUID string, ``uuid.UUID``, or ``None``.
    session:
        An active SQLAlchemy async session.
    company:
        An optional pre-loaded ``Company`` instance.  When supplied, *company_id*
        is ignored and no database query is executed.

    Returns
    -------
    Company
        The resolved and validated ``Company`` ORM instance.

    Raises
    ------
    NotFoundError
        If the company cannot be resolved or does not exist in the database.
    """
    # Fast path: caller already has the object
    if company is not None and isinstance(company, Company):
        return company

    # Slow path: parse identifier → DB lookup
    if company_id is not None:
        parsed_uuid = _parse_uuid(company_id)

        stmt = select(Company).where(Company.id == parsed_uuid)
        result = await session.execute(stmt)
        company_obj = result.scalar_one_or_none()

        if company_obj is not None:
            return company_obj

    # Nothing worked — raise consistent error
    raise NotFoundError("Company", company_id)
