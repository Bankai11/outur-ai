from __future__ import annotations

from typing import Any
from core.llm.base import BaseLLMProvider

def generate_mock_data_for_schema(schema: dict, prompt: str = "", prop_name: str = "") -> Any:
    t = schema.get("type", "").upper()
    if t == "ARRAY":
        items_schema = schema.get("items", {})
        # If this is a company list
        if items_schema.get("properties", {}).get("website") is not None:
            co1 = generate_mock_data_for_schema(items_schema, prompt, prop_name)
            co1["name"] = "Stripe"
            co1["website"] = "https://stripe.com"
            co1["domain"] = "stripe.com"
            co1["linkedin_url"] = "https://linkedin.com/company/stripe"
            co1["evidence"] = [{"source_url": "https://stripe.com", "source_type": "Website"}]
            
            co2 = generate_mock_data_for_schema(items_schema, prompt, prop_name)
            co2["name"] = "Plaid"
            co2["website"] = "https://plaid.com"
            co2["domain"] = "plaid.com"
            co2["linkedin_url"] = "https://linkedin.com/company/plaid"
            co2["evidence"] = [{"source_url": "https://plaid.com", "source_type": "Website"}]
            return [co1, co2]
            
        # If this is a contact list
        if items_schema.get("properties", {}).get("full_name") is not None:
            c1 = generate_mock_data_for_schema(items_schema, prompt, prop_name)
            c1["full_name"] = "Alice Recruiter"
            c1["job_title"] = "Talent Manager"
            c1["email"] = "alice@stripe.com" if "stripe" in prompt.lower() else "alice@company.com"
            c1["linkedin_url"] = "https://linkedin.com/in/alice"
            c1["evidence"] = [{"source_url": "https://linkedin.com/in/alice", "source_type": "LinkedIn"}]
            return [c1]
            
        return [generate_mock_data_for_schema(items_schema, prompt, prop_name)]
        
    elif t == "OBJECT":
        res = {}
        for p_name, prop_schema in schema.get("properties", {}).items():
            res[p_name] = generate_mock_data_for_schema(prop_schema, prompt, p_name)
        return res
        
    elif t == "STRING":
        desc = schema.get("description", "").lower()
        if "url" in desc or "link" in desc or "url" in prop_name.lower() or "link" in prop_name.lower():
            return "https://stripe.com" if "stripe" in prompt.lower() else "https://mockevidence.com/source"
        if "subject" in desc:
            return "Streamlining your recruitment pipeline"
        if "body" in desc:
            return "Hi, we can help automate candidate sourcing."
            
        if prop_name.lower() == "industry":
            if "fintech" in prompt.lower() or "fintech" in desc:
                return "FinTech"
            if "saas" in prompt.lower() or "saas" in desc:
                return "SaaS"
            return "FinTech"
            
        if prop_name.lower() == "classification":
            if "not looking to change" in prompt.lower():
                return "Not interested"
            if "next tuesday" in prompt.lower():
                return "Interested"
            if "remove me" in prompt.lower():
                return "Not interested"
            if "not the right person" in prompt.lower():
                return "Wrong contact"
            if "don't have the budget" in prompt.lower():
                return "Budget issue"
            return "Interested"
            
        if prop_name.lower() == "is_positive":
            return "next tuesday" in prompt.lower()

        if prop_name.lower() == "objection_identified":
            if "don't have the budget" in prompt.lower():
                return "No budget"
            return ""
            
        if prop_name.lower() == "competitor_mentioned":
            if "cultureamp" in prompt.lower():
                return "CultureAmp"
            return ""

        if "stripe" in prompt.lower():
            return "Stripe is a payments company."
        if "plaid" in prompt.lower():
            return "Plaid is a fintech company."
        return "Mock Value"
        
    elif t == "INTEGER":
        return 85
    elif t == "NUMBER":
        return 0.9
    elif t == "BOOLEAN":
        if prop_name.lower() == "is_positive":
            return "next tuesday" in prompt.lower()
        return True
    return None

class MockLLMProvider(BaseLLMProvider):
    async def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        use_search_grounding: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any] | None:
        def flatten_schema(s: dict) -> dict:
            import copy
            s = copy.deepcopy(s)
            defs = s.pop("$defs", {})
            def replace_refs(obj):
                if isinstance(obj, dict):
                    if "$ref" in obj:
                        ref = obj.pop("$ref")
                        if ref.startswith("#/$defs/"):
                            def_name = ref.replace("#/$defs/", "")
                            obj.update(replace_refs(copy.deepcopy(defs.get(def_name, {}))))
                        return obj
                    return {k: replace_refs(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [replace_refs(v) for v in obj]
                return obj
            return replace_refs(s)
            
        flat_schema = flatten_schema(schema)
        return generate_mock_data_for_schema(flat_schema, prompt)
