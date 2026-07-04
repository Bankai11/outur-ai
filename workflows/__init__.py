"""
Workflows package.

Workflows orchestrate multiple agents into a coordinated pipeline.
Each workflow defines the sequence of agent calls, data transformations,
error handling, and retry logic.

Pipeline overview
-----------------
::

    DiscoveryWorkflow
        Scout Agent → Enrichment Agent → Scorer Agent

    OutreachWorkflow
        Researcher Agent → Outreach Agent → Followup Agent

    FullPipelineWorkflow
        Scout → Enrichment → Researcher → Scorer → Outreach → Followup
"""

from workflows.base import BaseWorkflow

__all__ = ["BaseWorkflow"]
