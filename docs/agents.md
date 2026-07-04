# Agent Contracts — Outur AI

This document defines the **interface contract** for each agent in the Outur AI pipeline.
Agents must honour this contract when implemented so the workflow orchestrator
can call them interchangeably.

---

## Base Interface

Every agent exposes a single async `run()` method:

```python
class BaseAgent:
    agent_name: str

    async def run(self, **kwargs) -> dict[str, object]:
        """Execute the agent and return a structured result."""
        ...
```

The result dict must always contain:

| Key       | Type    | Description                          |
|-----------|---------|--------------------------------------|
| `success` | `bool`  | Whether the agent completed without fatal errors |
| `data`    | `dict`  | Agent-specific output payload        |
| `errors`  | `list`  | List of non-fatal error messages     |

---

## Scout Agent

**Package:** `agents/scout/`
**Status:** Phase 1

### Inputs

| Parameter | Type   | Description                              |
|-----------|--------|------------------------------------------|
| `icp`     | `dict` | Ideal Customer Profile filters           |
| `limit`   | `int`  | Max companies to return (default: 50)    |

### ICP Filter Schema

```json
{
  "industries": ["SaaS", "FinTech"],
  "headcount_min": 50,
  "headcount_max": 500,
  "geographies": ["US", "UK", "EU"],
  "technologies": ["Salesforce", "HubSpot"]
}
```

### Output

```json
{
  "success": true,
  "data": {
    "companies": [
      { "name": "Acme Corp", "domain": "acme.com", "source": "apollo" }
    ],
    "total_found": 42,
    "new_count": 15
  },
  "errors": []
}
```

---

## Enrichment Agent

**Package:** `agents/enrichment/`
**Status:** Phase 2

### Inputs

| Parameter    | Type         | Description                       |
|--------------|--------------|-----------------------------------|
| `company_id` | `UUID`       | ID of company to enrich           |
| `fields`     | `list[str]`  | Fields to enrich (default: all)   |

### Output

```json
{
  "success": true,
  "data": {
    "company_id": "uuid",
    "enriched_fields": ["headcount", "funding", "tech_stack"],
    "headcount": 200,
    "funding_stage": "Series B",
    "tech_stack": ["Salesforce", "Slack"]
  },
  "errors": []
}
```

---

## Scorer Agent

**Package:** `agents/scorer/`
**Status:** Phase 2

### Inputs

| Parameter    | Type   | Description                    |
|--------------|--------|--------------------------------|
| `company_id` | `UUID` | ID of company to score         |
| `icp`        | `dict` | ICP criteria for scoring       |

### Output

```json
{
  "success": true,
  "data": {
    "company_id": "uuid",
    "score": 87,
    "tier": "A",
    "signals": ["recent_hire", "funding_event", "tech_match"]
  },
  "errors": []
}
```

---

## Researcher Agent

**Package:** `agents/researcher/`
**Status:** Phase 3

### Inputs

| Parameter    | Type   | Description                           |
|--------------|--------|---------------------------------------|
| `company_id` | `UUID` | Company to research                   |
| `persona`    | `str`  | Target persona (e.g. "Head of Sales") |

### Output

```json
{
  "success": true,
  "data": {
    "contacts": [
      {
        "name": "Jane Smith",
        "title": "VP of Sales",
        "linkedin_url": "https://linkedin.com/in/...",
        "personalisation_context": "Recently spoke at SaaStr about..."
      }
    ]
  },
  "errors": []
}
```

---

## Outreach Agent

**Package:** `agents/outreach/`
**Status:** Phase 3

### Inputs

| Parameter    | Type   | Description                         |
|--------------|--------|-------------------------------------|
| `contact_id` | `UUID` | Contact to send outreach to         |
| `channel`    | `str`  | `"email"` or `"linkedin"`           |
| `template`   | `str`  | Prompt template name (optional)     |

### Output

```json
{
  "success": true,
  "data": {
    "contact_id": "uuid",
    "channel": "email",
    "message_id": "uuid",
    "subject": "Quick question about your sales process",
    "sent_at": "2025-01-01T12:00:00Z"
  },
  "errors": []
}
```

---

## Followup Agent

**Package:** `agents/followup/`
**Status:** Phase 4

### Inputs

| Parameter    | Type   | Description                           |
|--------------|--------|---------------------------------------|
| `campaign_id`| `UUID` | Campaign to manage follow-ups for     |

### Output

```json
{
  "success": true,
  "data": {
    "follow_ups_sent": 12,
    "replies_detected": 3,
    "positive_replies": 2,
    "meetings_booked": 1
  },
  "errors": []
}
```
