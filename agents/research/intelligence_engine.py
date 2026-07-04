"""
Research Intelligence Engine

Processes raw enrichment data into structured intelligence for companies.
Includes WhyNowEngine and OpportunityScorer.
"""

from typing import Any
import asyncio
from core.llm import get_llm_provider
from core.logger import get_logger

log = get_logger(__name__)


class OpportunityScorer:
    """Calculates an Opportunity Score based on specific signals."""
    
    @staticmethod
    def calculate_score(signals: dict[str, bool]) -> int:
        """
        - Recent funding (+20)
        - Hiring HR roles (+30)
        - Mentions AI on careers page (+15)
        - Growing engineering team (+25)
        - High revenue/employee ratio (+10)
        """
        score = 0
        if signals.get("recent_funding_identified"):
            score += 20
        if signals.get("hiring_hr_roles"):
            score += 30
        if signals.get("mentions_ai_on_careers"):
            score += 15
        if signals.get("growing_engineering_team"):
            score += 25
        if signals.get("high_revenue_employee_ratio"):
            score += 10
            
        return min(score, 100)


class WhyNowEngine:
    """Analyzes why the company would buy today."""
    
    @staticmethod
    async def analyze(company_name: str, signals: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Takes raw signals and outputs a structured why-now analysis.
        """
        llm = get_llm_provider()
        
        schema = {
            "type": "OBJECT",
            "properties": {
                "chain_of_reasoning": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "Example: ['Hiring increased 45%', 'Scaling rapidly', 'Likely overwhelmed recruiting team', 'Perfect timing for outreach']"
                },
                "why_now_score": {
                    "type": "INTEGER",
                    "description": "A score from 0-100 indicating urgency based on the chain of reasoning."
                },
                "summary": {
                    "type": "STRING",
                    "description": "Short 1 sentence summary of the why now logic."
                }
            },
            "required": ["chain_of_reasoning", "why_now_score", "summary"]
        }
        
        prompt = (
            f"Analyze the following signals for {company_name} and determine why they need outreach today.\n"
            f"Signals: {signals}\n"
            f"Construct a logical chain of reasoning and assign an urgency score (why_now_score)."
        )
        
        result = await llm.generate_json(prompt, schema)
        if result:
            return result
        return {
            "chain_of_reasoning": ["No signals identified"],
            "why_now_score": 0,
            "summary": "Not enough data to determine urgency."
        }


class ResearchIntelligenceEngine:
    """
    Produces structured company intelligence.
    """

    async def analyze_company(
        self,
        company_name: str,
        domain: str | None,
        enrichment_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Process enrichment data into a full ResearchProfile structure.
        """
        llm = get_llm_provider()
        
        schema = {
            "type": "OBJECT",
            "properties": {
                "employees": {"type": "INTEGER"},
                "revenue_estimated": {"type": "STRING"},
                "funding": {
                    "type": "OBJECT",
                    "properties": {
                        "latest_round": {"type": "STRING"},
                        "amount": {"type": "STRING"},
                        "date": {"type": "STRING"}
                    }
                },
                "technologies_used": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"}
                },
                "competitors": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"}
                },
                "hr_maturity": {"type": "STRING"},
                "recent_news": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "title": {"type": "STRING"},
                            "url": {"type": "STRING"},
                            "date": {"type": "STRING"}
                        },
                        "required": ["title", "url"]
                    }
                },
                "hiring_signals": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "insight": {"type": "STRING"},
                            "source_url": {"type": "STRING"}
                        },
                        "required": ["insight", "source_url"]
                    }
                },
                "growth_indicators": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "insight": {"type": "STRING"},
                            "source_url": {"type": "STRING"}
                        },
                        "required": ["insight", "source_url"]
                    }
                },
                "public_pain_points": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "insight": {"type": "STRING"},
                            "source_url": {"type": "STRING"}
                        },
                        "required": ["insight", "source_url"]
                    }
                },
                "ai_adoption_signals": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "insight": {"type": "STRING"},
                            "source_url": {"type": "STRING"}
                        },
                        "required": ["insight", "source_url"]
                    }
                },
                "opportunity_signals": {
                    "type": "OBJECT",
                    "properties": {
                        "recent_funding_identified": {"type": "BOOLEAN"},
                        "hiring_hr_roles": {"type": "BOOLEAN"},
                        "mentions_ai_on_careers": {"type": "BOOLEAN"},
                        "growing_engineering_team": {"type": "BOOLEAN"},
                        "high_revenue_employee_ratio": {"type": "BOOLEAN"}
                    },
                    "required": [
                        "recent_funding_identified", 
                        "hiring_hr_roles", 
                        "mentions_ai_on_careers", 
                        "growing_engineering_team", 
                        "high_revenue_employee_ratio"
                    ]
                }
            },
            "required": [
                "technologies_used", 
                "competitors", 
                "recent_news", 
                "hiring_signals", 
                "growth_indicators", 
                "public_pain_points", 
                "ai_adoption_signals",
                "opportunity_signals"
            ]
        }
        
        prompt = (
            f"Extract structured company intelligence for '{company_name}' ({domain}).\n"
            f"Use the following raw enrichment data:\n{enrichment_data}\n"
            f"Make sure to extract explicit opportunity signals to help scoring."
        )
        
        log.info(f"Running LLM extraction for {company_name}")
        profile_data = await llm.generate_json(prompt, schema)
        
        if not profile_data:
            log.warning(f"Failed to generate structured profile for {company_name}, falling back to defaults.")
            profile_data = {
                "technologies_used": [],
                "competitors": [],
                "recent_news": [],
                "hiring_signals": [],
                "growth_indicators": [],
                "public_pain_points": [],
                "ai_adoption_signals": [],
                "opportunity_signals": {
                    "recent_funding_identified": False,
                    "hiring_hr_roles": False,
                    "mentions_ai_on_careers": False,
                    "growing_engineering_team": False,
                    "high_revenue_employee_ratio": False
                }
            }

        # Calculate opportunity score
        signals = profile_data.get("opportunity_signals", {})
        opportunity_score = OpportunityScorer.calculate_score(signals)
        profile_data["opportunity_score"] = opportunity_score
        
        # Combine signals for the why now engine
        combined_signals = (
            profile_data.get("hiring_signals", []) + 
            profile_data.get("growth_indicators", []) +
            profile_data.get("recent_news", [])
        )
        
        why_now_data = await WhyNowEngine.analyze(company_name, combined_signals)
        
        profile_data["why_now_analysis"] = why_now_data
        profile_data["why_now_score"] = why_now_data.get("why_now_score", 0)
        
        return profile_data
