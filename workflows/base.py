"""
Abstract base class for all Outur AI workflows.

A workflow is a stateful orchestrator that coordinates one or more agents
to achieve a higher-level business objective.

Design principles
-----------------
- Each workflow is a pure Python class — no framework magic.
- Workflows are async-first and support cancellation.
- State is passed explicitly between steps; no hidden shared state.
- Every step is logged with structured events for observability.
- Failures surface as typed exceptions, not silent errors.

Implementing a workflow
-----------------------
::

    from workflows.base import BaseWorkflow, WorkflowResult

    class DiscoveryWorkflow(BaseWorkflow):
        name = "discovery"

        async def execute(self, **kwargs) -> WorkflowResult:
            self.log.info("Starting discovery", **kwargs)
            # 1. Scout
            # 2. Enrich
            # 3. Score
            return WorkflowResult(success=True, data={})
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.logger import get_logger


@dataclass
class WorkflowResult:
    """
    Typed result returned by every workflow's ``execute()`` method.

    Attributes
    ----------
    success:
        True if the workflow completed without fatal errors.
    data:
        Arbitrary structured output from the workflow (schema is workflow-specific).
    errors:
        List of error messages accumulated during execution.
    started_at:
        UTC timestamp when execution began.
    finished_at:
        UTC timestamp when execution completed (set automatically).
    """

    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None

    def complete(self) -> None:
        """Mark the workflow as finished by recording the completion timestamp."""
        self.finished_at = datetime.now(timezone.utc)

    @property
    def duration_seconds(self) -> float | None:
        """Return elapsed seconds between start and finish, or None if not finished."""
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()


class BaseWorkflow(ABC):
    """
    Abstract base for all Outur AI workflows.

    Subclasses must:
    1. Define ``name`` — a unique snake_case identifier.
    2. Implement ``execute(**kwargs) -> WorkflowResult``.

    The ``run()`` method wraps ``execute()`` with logging, timing, and
    error boundaries — subclasses should override ``execute()``, not ``run()``.
    """

    #: Unique snake_case name for this workflow (e.g. "discovery", "outreach")
    name: str = "base"

    def __init__(self) -> None:
        self.log = get_logger(f"workflows.{self.name}")

    @abstractmethod
    async def execute(self, **kwargs: Any) -> WorkflowResult:
        """
        Core workflow logic. Must be implemented by subclasses.

        Parameters
        ----------
        **kwargs:
            Workflow-specific input parameters.

        Returns
        -------
        WorkflowResult
            Structured outcome of the workflow execution.
        """
        ...

    async def run(self, **kwargs: Any) -> WorkflowResult:
        """
        Public entry point. Wraps ``execute()`` with observability.

        - Logs start/finish events with duration
        - Catches unexpected exceptions and surfaces them in WorkflowResult
        - Always returns a WorkflowResult (never re-raises raw exceptions)
        """
        self.log.info("Workflow starting", workflow=self.name, input_keys=list(kwargs.keys()))

        result = WorkflowResult(success=False)

        try:
            result = await self.execute(**kwargs)
        except Exception as exc:  # noqa: BLE001
            result.success = False
            result.errors.append(str(exc))
            self.log.error(
                "Workflow failed with unhandled exception",
                workflow=self.name,
                exc_info=exc,
            )
        finally:
            result.complete()
            self.log.info(
                "Workflow finished",
                workflow=self.name,
                success=result.success,
                duration_s=result.duration_seconds,
                error_count=len(result.errors),
            )

        return result
