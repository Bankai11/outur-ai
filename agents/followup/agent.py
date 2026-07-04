"""Followup Agent — STUB. Manages follow-up sequences and tracks reply sentiment and status."""
from __future__ import annotations
from core.logger import get_logger
log = get_logger(__name__)

class FollowupAgent:
    """Manages follow-up sequences and reply tracking. Status: STUB."""
    agent_name: str = "followup"
    def __init__(self) -> None:
        log.debug("FollowupAgent initialised (stub)", agent=self.agent_name)
    async def run(self, **kwargs: object) -> dict[str, object]:
        raise NotImplementedError("FollowupAgent.run() not yet implemented.")
