"""
Sales Intelligence Engine

Processes raw enrichment data into structured intelligence for companies.
Refactored to support configurable outbound outreach via 4 modular LLM prompts.
"""

import asyncio
from typing import Any

from core.llm import get_llm_provider
from core.logger import get_logger
from core.config.business_profile import get_business_profile

log = get_logger(__name__)


class SalesIntelligenceEngine:
    """
    Produces highly structured sales intelligence for configured outreach.
    Splits generation into modular prompts to ensure grounding and quality.
    """

    def __init__(self) -> None:
        self.llm = get_llm_provider()
        self.profile = get_business_profile()

    async def analyze_company(
        self,
        company_name: str,
        domain: str | None,
        enrichment_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Orchestrates the 4-step intelligence generation pipeline.
        """
        log.info(f"Running modular sales intelligence pipeline for {company_name}")

        # Step 1: Research (Business Context & Signals)
        business_context = await self._extract_business_context(company_name, domain, enrichment_data)
        
        # Step 2: Sales Intelligence (Pain points, initiatives, risks)
        sales_intel = await self._extract_sales_intelligence(company_name, business_context)

        # Step 3: Product Mapping (How our configured product fits into their pain points)
        product_mapping = await self._map_product_value(company_name, business_context, sales_intel)

        # Step 4: Personalization (Actionable outreach recommendations)
        outreach_intel = await self._generate_outreach_intelligence(
            company_name, business_context, sales_intel, product_mapping
        )

        # Merge results
        profile_data = {}
        profile_data.update(business_context)
        profile_data.update(sales_intel)
        profile_data.update(product_mapping)
        profile_data.update(outreach_intel)

        # Base confidence calculation
        pain_points = profile_data.get("pain_points", [])
        avg_pain_conf = sum(p.get("confidence", 0) for p in pain_points) / max(len(pain_points), 1)
        profile_data["confidence_score"] = int(avg_pain_conf) if pain_points else 50
        
        # Collect sources
        sources = set()
        for key in ["hiring_signals", "buying_signals", "digital_transformation_signals", "recent_news"]:
            for item in profile_data.get(key, []):
                if isinstance(item, dict) and "source_url" in item:
                    sources.add(item["source_url"])
                elif isinstance(item, dict) and "url" in item:
                    sources.add(item["url"])
        profile_data["supporting_sources"] = list(sources)

        return profile_data

    async def _extract_business_context(self, company_name: str, domain: str | None, enrichment_data: dict[str, Any]) -> dict[str, Any]:
        schema = {
            "type": "OBJECT",
            "properties": {
                "executive_summary": {"type": "STRING"},
                "business_overview": {"type": "STRING"},
                "business_model": {"type": "STRING"},
                "target_customers": {"type": "STRING"},
                "products_services": {"type": "STRING"},
                "growth_stage": {"type": "STRING"},
                "technology_stack": {"type": "ARRAY", "items": {"type": "STRING"}},
                "hiring_activity": {"type": "STRING"},
                "recent_news": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "title": {"type": "STRING"},
                            "url": {"type": "STRING"}
                        },
                        "required": ["title", "url"]
                    }
                },
                "recent_funding": {
                    "type": "OBJECT",
                    "properties": {
                        "amount": {"type": "STRING"},
                        "date": {"type": "STRING"}
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
                        "required": ["insight"]
                    }
                },
                "buying_signals": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "insight": {"type": "STRING"},
                            "source_url": {"type": "STRING"}
                        },
                        "required": ["insight"]
                    }
                },
                "digital_transformation_signals": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "insight": {"type": "STRING"},
                            "source_url": {"type": "STRING"}
                        },
                        "required": ["insight"]
                    }
                }
            },
            "required": ["executive_summary", "technology_stack", "hiring_signals", "buying_signals"]
        }

        # Provide the list of configured triggers to help the LLM identify one
        trigger_names = [t.event for t in self.profile.triggers]
        prompt = (
            f"Analyze raw enrichment data for '{company_name}' ({domain}).\n"
            f"Extract factual business context and signals. Do not hallucinate.\n"
            f"Look out specifically for these trigger events if present: {trigger_names}\n"
            f"Raw Data:\n{enrichment_data}"
        )
        result = await self.llm.generate_json(prompt, schema)
        return result or {
            "executive_summary": "",
            "technology_stack": [],
            "hiring_signals": [],
            "buying_signals": [],
            "digital_transformation_signals": [],
            "recent_news": []
        }

    async def _extract_sales_intelligence(self, company_name: str, business_context: dict[str, Any]) -> dict[str, Any]:
        schema = {
            "type": "OBJECT",
            "properties": {
                "strategic_initiatives": {"type": "STRING"},
                "competitive_landscape": {"type": "STRING"},
                "key_differentiators": {"type": "STRING"},
                "potential_decision_makers": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "title": {"type": "STRING"},
                            "reasoning": {"type": "STRING"}
                        },
                        "required": ["title", "reasoning"]
                    }
                },
                "communication_style": {"type": "STRING"},
                "risk_assessment": {"type": "STRING"},
                "sales_opportunity_summary": {"type": "STRING"},
                "pain_points": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "pain_point": {"type": "STRING"},
                            "confidence": {"type": "INTEGER", "description": "0-100"},
                            "supporting_evidence": {"type": "STRING"},
                            "reasoning": {"type": "STRING"}
                        },
                        "required": ["pain_point", "confidence", "supporting_evidence", "reasoning"]
                    },
                    "description": "Inferred business or HR pain points."
                },
                "primary_trigger": {
                    "type": "STRING",
                    "description": "The single most compelling reason to reach out right now, selected from the business context signals."
                }
            },
            "required": ["pain_points", "potential_decision_makers", "sales_opportunity_summary", "primary_trigger"]
        }

        prompt = (
            f"Act as a Senior Sales Analyst for '{company_name}'.\n"
            f"Using the business context, infer likely pain points, strategic initiatives, and decision makers.\n"
            f"Be highly specific. Pain points MUST include confidence (0-100), evidence, and reasoning.\n"
            f"Business Context:\n{business_context}"
        )
        result = await self.llm.generate_json(prompt, schema)
        return result or {
            "pain_points": [],
            "potential_decision_makers": [],
            "sales_opportunity_summary": "",
            "primary_trigger": ""
        }

    async def _map_product_value(self, company_name: str, business_context: dict[str, Any], sales_intel: dict[str, Any]) -> dict[str, Any]:
        schema = {
            "type": "OBJECT",
            "properties": {
                "product_value_mapping": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "use_case": {"type": "STRING"},
                            "value_prop": {"type": "STRING"},
                            "reasoning": {"type": "STRING"},
                            "confidence": {"type": "INTEGER", "description": "0-100"}
                        },
                        "required": ["use_case", "value_prop", "reasoning", "confidence"]
                    },
                    "description": f"Map company pain points to {self.profile.product_name} use cases."
                },
                "recommended_playbook": {
                    "type": "STRING",
                    "description": "The exact name of the best playbook to use based on the primary_trigger."
                }
            },
            "required": ["product_value_mapping", "recommended_playbook"]
        }

        playbook_details = "\n".join([f"- {p.name}: {p.messaging_strategy} (Triggers: {p.target_triggers})" for p in self.profile.playbooks])
        
        prompt = (
            f"{self.profile.product_name} is a platform focusing on: {self.profile.elevator_pitch}\n"
            f"Core pain points solved: {', '.join(self.profile.core_pain_points_solved)}\n"
            f"Map the identified pain points of '{company_name}' to specific {self.profile.product_name} value propositions.\n"
            f"Also, select the single best playbook from the list below based on their primary trigger: {sales_intel.get('primary_trigger')}.\n"
            f"Available Playbooks:\n{playbook_details}\n\n"
            f"Do NOT fabricate use cases. Only produce mappings supported by the research.\n\n"
            f"Pain Points: {sales_intel.get('pain_points', [])}\n"
            f"Growth/Hiring Signals: {business_context.get('hiring_signals', [])}\n"
        )
        result = await self.llm.generate_json(prompt, schema)
        return result or {"product_value_mapping": [], "recommended_playbook": ""}

    async def _generate_outreach_intelligence(self, company_name: str, business_context: dict[str, Any], sales_intel: dict[str, Any], product_mapping: dict[str, Any]) -> dict[str, Any]:
        schema = {
            "type": "OBJECT",
            "properties": {
                "outreach_intelligence": {
                    "type": "OBJECT",
                    "properties": {
                        "best_opening_sentence": {"type": "STRING"},
                        "relevant_achievement": {"type": "STRING"},
                        "relevant_pain_point": {"type": "STRING"},
                        "recommended_tone": {"type": "STRING"},
                        "recommended_email_length": {"type": "STRING"},
                        "recommended_cta": {"type": "STRING"},
                        "topics_to_avoid": {"type": "ARRAY", "items": {"type": "STRING"}},
                        "topics_to_emphasize": {"type": "ARRAY", "items": {"type": "STRING"}}
                    },
                    "required": [
                        "best_opening_sentence", "relevant_achievement", "relevant_pain_point",
                        "recommended_tone", "recommended_cta", "topics_to_avoid", "topics_to_emphasize"
                    ]
                }
            },
            "required": ["outreach_intelligence"]
        }

        prompt = (
            f"Generate actionable outreach intelligence for contacting '{company_name}'.\n"
            f"Synthesize the {self.profile.product_name} value proposition and the company's pain points into a tailored outreach strategy.\n"
            f"The primary trigger for this outreach is: {sales_intel.get('primary_trigger', 'General outreach')}\n"
            f"The recommended playbook is: {product_mapping.get('recommended_playbook', 'General')}\n"
            f"Pain Points: {sales_intel.get('pain_points', [])}\n"
            f"Product Mappings: {product_mapping.get('product_value_mapping', [])}\n"
            f"Recent News/Achievements: {business_context.get('recent_news', [])}\n"
            f"Configured Tone: {self.profile.email_tone}\n"
            f"Forbidden Claims: {', '.join(self.profile.forbidden_claims)}\n"
        )
        result = await self.llm.generate_json(prompt, schema)
        return result or {
            "outreach_intelligence": {
                "best_opening_sentence": f"Noticed your recent growth at {company_name}.",
                "relevant_achievement": "Recent growth",
                "relevant_pain_point": "Scaling",
                "recommended_tone": self.profile.email_tone,
                "recommended_email_length": "Short",
                "recommended_cta": "Open to a brief chat?",
                "topics_to_avoid": self.profile.forbidden_claims,
                "topics_to_emphasize": []
            }
        }
