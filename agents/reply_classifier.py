"""
Reply Classifier Agent

Analyzes an incoming email reply to classify the prospect's response,
determine their level of interest, and extract any objections to help
refine outreach playbooks.
"""

from typing import Any

from core.llm import get_llm_provider
from core.logger import get_logger

log = get_logger(__name__)

# Core tracking categories
REPLY_CATEGORIES = [
    "Interested",
    "Not interested",
    "Wrong contact",
    "Budget issue",
    "Timing issue",
    "Booked demo",
    "Questions/More Info Needed",
    "Spam/Bounced"
]


class ReplyClassifierAgent:
    """
    Analyzes an email reply and original outreach to classify the prospect's sentiment and objections.
    """

    agent_name: str = "reply_classifier"

    def __init__(self) -> None:
        self.llm = get_llm_provider()

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        """
        Execute the Reply Classifier Agent.

        Parameters
        ----------
        reply_text: str
            The raw text of the incoming reply.
        original_email: str | None
            The text of the original outbound email (for context).
        prospect_name: str | None
            Name of the prospect.
        company_name: str | None
            Name of the prospect's company.
        """
        log.info("Running Reply Classifier Agent")

        reply_text = kwargs.get("reply_text")
        original_email = kwargs.get("original_email", "Not provided")
        prospect_name = kwargs.get("prospect_name", "Unknown")
        company_name = kwargs.get("company_name", "Unknown")

        if not reply_text:
            return {
                "success": False,
                "data": {},
                "errors": ["reply_text is required"]
            }

        try:
            classification = await self._classify_reply(
                reply_text=reply_text,
                original_email=original_email,
                prospect_name=prospect_name,
                company_name=company_name
            )

            return {
                "success": True,
                "data": classification,
                "errors": []
            }
        except Exception as e:
            log.error("Failed to run Reply Classifier Agent", error=str(e))
            return {
                "success": False,
                "data": {},
                "errors": [str(e)]
            }

    async def _classify_reply(
        self,
        reply_text: str,
        original_email: str,
        prospect_name: str,
        company_name: str
    ) -> dict[str, Any]:
        """
        Calls the LLM to classify the reply and extract objections.
        """
        schema = {
            "type": "OBJECT",
            "properties": {
                "classification": {
                    "type": "STRING",
                    "description": f"Must be one of the following exact categories: {', '.join(REPLY_CATEGORIES)}"
                },
                "is_positive": {
                    "type": "BOOLEAN",
                    "description": "True if the response is generally positive/interested, False if negative/rejected."
                },
                "objection_identified": {
                    "type": "STRING",
                    "description": "If the prospect raises an objection (e.g. 'we use a competitor', 'no budget'), summarize it here. Leave empty if none."
                },
                "competitor_mentioned": {
                    "type": "STRING",
                    "description": "If a competitor is explicitly mentioned, list it here."
                },
                "next_steps_requested": {
                    "type": "STRING",
                    "description": "If the prospect asks for a meeting, more info, or suggests a time, summarize it here."
                },
                "reasoning": {
                    "type": "STRING",
                    "description": "Brief explanation of why this classification was chosen."
                }
            },
            "required": ["classification", "is_positive", "reasoning"]
        }

        prompt = (
            f"You are a sales operations AI analyzing an email reply from a prospect.\n\n"
            f"Prospect: {prospect_name} at {company_name}\n\n"
            f"--- ORIGINAL OUTBOUND EMAIL ---\n"
            f"{original_email}\n\n"
            f"--- PROSPECT'S REPLY ---\n"
            f"{reply_text}\n\n"
            f"Analyze the prospect's reply. Categorize it strictly into one of these categories: {REPLY_CATEGORIES}.\n"
            f"Extract any objections, competitor mentions, or requested next steps."
        )

        result = await self.llm.generate_json(prompt, schema)
        
        # Enforce exact category matching
        classification = result.get("classification")
        if classification not in REPLY_CATEGORIES:
            # Fallback handling
            log.warning(f"LLM returned non-standard classification: {classification}")
            if result.get("is_positive"):
                result["classification"] = "Interested"
            else:
                result["classification"] = "Not interested"

        return result
