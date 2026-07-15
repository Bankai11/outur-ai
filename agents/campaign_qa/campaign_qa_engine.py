"""Campaign QA Engine module for evaluating and verifying generated outreach emails."""

from typing import Any
from core.llm import get_llm_provider
from core.logger import get_logger
from core.models.company import Company
from core.models.contact import Contact
from core.models.sales_intelligence import SalesIntelligenceProfile

log = get_logger(__name__)

QA_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "overall_score": {"type": "INTEGER", "description": "Score out of 100 representing the overall email quality."},
        "accuracy_score": {"type": "INTEGER", "description": "Score out of 100 for factual accuracy."},
        "personalization_score": {"type": "INTEGER", "description": "Score out of 100 for personalization depth and relevance."},
        "grammar_score": {"type": "INTEGER", "description": "Score out of 100 for spelling, grammar, and readability."},
        "cta_score": {"type": "INTEGER", "description": "Score out of 100 for CTA clarity and strength."},
        "tone_score": {"type": "INTEGER", "description": "Score out of 100 for appropriate professional tone."},
        "hallucination_score": {"type": "INTEGER", "description": "Score out of 100 where 100 means NO hallucinations."},
        "issues": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "Specific issues found in the email (e.g., hallucinated facts, poor grammar)."
        },
        "recommendations": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "Actionable recommendations on how to fix the issues."
        },
        "approved": {"type": "BOOLEAN", "description": "Whether the email meets all quality standards and can be sent."}
    },
    "required": [
        "overall_score",
        "accuracy_score",
        "personalization_score",
        "grammar_score",
        "cta_score",
        "tone_score",
        "hallucination_score",
        "issues",
        "recommendations",
        "approved"
    ]
}


class CampaignQAEngine:
    """Evaluates outreach drafts for quality, personalization, and hallucinations."""

    def __init__(self):
        self.llm = get_llm_provider()

    async def evaluate_email(
        self,
        subject: str,
        body: str,
        contact: Contact,
        company: Company,
        profile: SalesIntelligenceProfile | None
    ) -> dict[str, Any]:
        """
        Evaluate an outreach email against a strict rubric.
        Ensures no hallucinations or poor messaging.
        """
        log.info("Running Campaign QA evaluation", contact=contact.email)
        
        # Build context
        context_str = f"Company: {company.name}\nContact: {contact.full_name} ({contact.job_title})\n"
        if profile:
            context_str += f"Business Context: {profile.executive_summary}\n"
            pain_str = ", ".join([p.get("pain_point", "") for p in profile.pain_points])
            context_str += f"Pain Points: {pain_str}\n"
            news_str = ", ".join([n.get("title", "") for n in profile.recent_news])
            context_str += f"Recent News/Achievements: {news_str}\n"
            hiring = ", ".join([h.get("insight", "") for h in profile.hiring_signals])
            context_str += f"Hiring Signals: {hiring}\n"
        
        prompt = f"""
You are an expert Sales QA Analyst. Your job is to rigorously evaluate a drafted cold email.
You must ensure it is factually accurate, highly personalized, and free of any hallucinations.
You must fail (approved = false) ANY email that makes claims about the company's funding, hiring, technology, or achievements that are NOT explicitly supported by the provided context.

Context Data (ONLY rely on this data for facts):
{context_str}

Email Draft to Evaluate:
Subject: {subject}
Body: {body}

Evaluate the email against the following criteria:
1. Hallucinations: Does the email invent any facts, news, funding amounts, or specific details not present in the Context Data? If yes, hallucination_score < 50 and approved MUST be false.
2. Personalization: Is the personalization relevant and natural, or does it feel generic/forced?
3. Grammar and Tone: Is it professional, free of passive language, and devoid of spam trigger words?
4. Call to Action (CTA): Is there a single, clear, low-friction CTA?

Return a structured QA report matching the provided schema. If there are any hallucinations, poor grammar, or very weak personalization, approved MUST be false.
"""
        
        qa_report = await self.llm.generate_json(prompt, QA_SCHEMA)
        
        if not qa_report:
            log.error("QA Engine failed to generate a report.")
            return {
                "overall_score": 0,
                "accuracy_score": 0,
                "personalization_score": 0,
                "grammar_score": 0,
                "cta_score": 0,
                "tone_score": 0,
                "hallucination_score": 0,
                "issues": ["QA System Failure: Could not generate report."],
                "recommendations": [],
                "approved": False
            }
            
        return qa_report
