import json
import logging
from typing import Any
from core.llm import get_llm_provider
from agents.enrichment.models import EnrichmentResult

log = logging.getLogger(__name__)

class EnrichmentRepairer:
    """Attempts self-repair of malformed LLM outputs."""
    
    @staticmethod
    async def repair(raw_output: str | dict[str, Any], error_msg: str) -> dict[str, Any] | None:
        """
        Attempt to repair malformed output.
        If it's a string, try basic string cleanup.
        If it still fails or fails Pydantic validation, call LLM to fix it.
        """
        # Step 1: Basic JSON string repair if it's a string
        if isinstance(raw_output, str):
            cleaned = raw_output.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass # Fall through to LLM repair
                
        # Step 2: LLM Self-Repair
        llm = get_llm_provider()
        prompt = f"""
You are an expert JSON repair system.
The following enrichment data failed validation or could not be parsed.
Error: {error_msg}

Raw Data:
{raw_output if isinstance(raw_output, str) else json.dumps(raw_output)}

Please rewrite this data strictly adhering to the requested JSON schema.
Ensure all required fields are present and data types match.
"""
        log.warning(f"Attempting LLM self-repair due to error: {error_msg}")
        schema = EnrichmentResult.model_json_schema()
        
        # Max 1 retry
        try:
            repaired_json = await llm.generate_json(
                prompt=prompt,
                schema=schema,
                use_search_grounding=False, # Don't need search just to fix formatting
                timeout=20.0
            )
            return repaired_json
        except Exception as e:
            log.error(f"LLM self-repair failed: {str(e)}")
            return None
