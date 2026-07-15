import logging
from typing import Any
from agents.enrichment.models import EnrichmentResult
from agents.enrichment.validation.normalizer import EnrichmentNormalizer
from agents.enrichment.validation.confidence import ConfidenceEvaluator
from agents.enrichment.validation.repair import EnrichmentRepairer

log = logging.getLogger(__name__)

class ValidationPipeline:
    """Orchestrates validation, normalization, and confidence scoring."""

    @staticmethod
    async def process(raw_data: dict[str, Any] | str | None) -> EnrichmentResult:
        """
        Process the raw data through the validation pipeline.
        Returns a strongly typed EnrichmentResult.
        """
        if not raw_data:
            return EnrichmentResult(validation_status="failed", validation_errors=["No raw data provided."])

        errors = []
        data_to_validate = raw_data
        
        # 1. Basic structural check
        if isinstance(data_to_validate, str):
            repaired = await EnrichmentRepairer.repair(data_to_validate, "Raw data is a string instead of JSON dictionary.")
            if repaired:
                data_to_validate = repaired
            else:
                return EnrichmentResult(
                    raw_data={"raw": raw_data},
                    validation_status="failed",
                    validation_errors=["Failed to parse raw text into JSON."]
                )

        # 2. Normalize
        try:
            data_to_validate = EnrichmentNormalizer.normalize(data_to_validate)
        except Exception as e:
            err_msg = f"Normalization error: {str(e)}"
            log.warning(err_msg)
            errors.append(err_msg)

        # 3. Confidence Scoring
        try:
            data_to_validate = ConfidenceEvaluator.evaluate(data_to_validate)
        except Exception as e:
            err_msg = f"Confidence evaluation error: {str(e)}"
            log.warning(err_msg)
            errors.append(err_msg)

        # 4. Pydantic Validation
        try:
            result = EnrichmentResult.model_validate(data_to_validate)
            result.validation_status = "valid"
            result.validation_errors = errors
            return result
        except Exception as e:
            err_msg = f"Schema validation error: {str(e)}"
            log.warning(err_msg)
            errors.append(err_msg)
            
            # 5. Self-Repair on Schema Failure
            repaired = await EnrichmentRepairer.repair(data_to_validate, err_msg)
            if repaired:
                # Try normalization and confidence again on repaired data
                repaired = EnrichmentNormalizer.normalize(repaired)
                repaired = ConfidenceEvaluator.evaluate(repaired)
                try:
                    result = EnrichmentResult.model_validate(repaired)
                    result.validation_status = "repaired"
                    result.validation_errors = errors + ["Successfully repaired via LLM."]
                    return result
                except Exception as e2:
                    errors.append(f"Repair validation failed: {str(e2)}")

            # Total failure, return partial
            return EnrichmentResult(
                raw_data=data_to_validate,
                validation_status="failed",
                validation_errors=errors
            )
