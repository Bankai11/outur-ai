"""
Agents package — registry and shared agent infrastructure.

Each sub-package represents one autonomous agent in the Outur AI pipeline:

┌──────────────────────────────────────────────────────────────────────┐
│  Pipeline: Scout → Enrichment → Researcher → Scorer → Outreach       │
│            └─────────────────────────────────────> Followup           │
└──────────────────────────────────────────────────────────────────────┘

Agent         Responsibility
─────────     ──────────────────────────────────────────────────────────
scout         Discover target companies matching ICP criteria
enrichment    Enrich companies with HR, funding, and tech stack data
researcher    Research individuals and craft personalised context
scorer        Score leads by fit, intent, and timing signals
outreach      Generate and send personalised outreach messages
followup      Manage follow-up sequences and track responses
"""

# Agent registry — populated as agents are implemented
AGENT_REGISTRY: dict[str, str] = {
    "scout": "agents.scout.agent.ScoutAgent",
    "enrichment": "agents.enrichment.agent.EnrichmentAgent",
    "researcher": "agents.researcher.agent.ResearcherAgent",
    "scorer": "agents.scorer.agent.ScorerAgent",
    "outreach": "agents.outreach.agent.OutreachAgent",
    "followup": "agents.followup.agent.FollowupAgent",
}

__all__ = ["AGENT_REGISTRY"]
