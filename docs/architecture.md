# Architecture — Outur AI

## Overview

Outur AI is a multi-agent AI platform for B2B business development automation.
It is built on a **layered, async-first architecture** with strict separation between:

1. **API Layer** — FastAPI HTTP interface
2. **Workflow Layer** — Pipeline orchestration
3. **Agent Layer** — Autonomous AI agents (Antigravity SDK)
4. **Core Layer** — Shared infrastructure (DB, logging, config)

---

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        API Layer (FastAPI)                          │
│  /health  /ready  /api/v1/companies  /api/v1/leads  /api/v1/runs   │
└────────────────────────────┬────────────────────────────────────────┘
                             │ Dependency Injection (api/deps.py)
┌────────────────────────────▼────────────────────────────────────────┐
│                      Workflow Layer                                  │
│   DiscoveryWorkflow   OutreachWorkflow   FullPipelineWorkflow        │
└──────┬──────────┬──────────┬────────────┬──────────────┬────────────┘
       │          │          │            │              │
  ┌────▼──┐ ┌────▼──────┐ ┌─▼──────────┐ ┌▼──────┐ ┌───▼─────┐
  │ Scout │ │Enrichment │ │ Researcher │ │Scorer │ │Outreach │
  │ Agent │ │  Agent    │ │   Agent    │ │ Agent │ │  Agent  │
  └───┬───┘ └────┬──────┘ └─────┬──────┘ └───┬───┘ └───┬─────┘
      │          │              │             │          │
      └──────────┴──────────────┴─────────────┴──────────┘
                                │
           ┌────────────────────▼────────────────────────────────┐
           │                  Core Layer                          │
           │  config │ database │ logger │ models │ utils         │
           └─────────────────────────────────────────────────────┘
                                │
           ┌────────────────────▼────────────────────────────────┐
           │              Infrastructure                          │
           │   PostgreSQL 16    │    (future) Redis               │
           └─────────────────────────────────────────────────────┘
```

---

## Agent Pipeline

```
Input: ICP Configuration
        │
        ▼
┌──────────────┐     Finds matching companies
│ Scout Agent  │ ──► (Apollo, LinkedIn, web search)
└──────┬───────┘
       │ company list
       ▼
┌────────────────────┐   Adds HR, funding, tech stack
│ Enrichment Agent   │ ──► data from external APIs
└──────┬─────────────┘
       │ enriched companies
       ▼
┌────────────────────┐   Scores companies by ICP fit,
│  Scorer Agent      │ ──► intent signals, and timing
└──────┬─────────────┘
       │ scored + prioritised leads
       ▼
┌────────────────────┐   Researches individual contacts,
│ Researcher Agent   │ ──► builds personalised context
└──────┬─────────────┘
       │ contact + context
       ▼
┌────────────────────┐   Generates personalised emails/
│  Outreach Agent    │ ──► LinkedIn messages and sends them
└──────┬─────────────┘
       │ sent message
       ▼
┌────────────────────┐   Monitors replies, schedules
│  Followup Agent    │ ──► follow-ups, updates CRM status
└────────────────────┘
```

---

## Directory Responsibilities

| Directory       | Responsibility                                               |
|-----------------|--------------------------------------------------------------|
| `api/`          | HTTP routing, request/response validation, DI wiring         |
| `agents/`       | Autonomous agent logic + tool functions per agent            |
| `workflows/`    | Multi-agent orchestration, retry, error handling             |
| `core/config/`  | All env-driven configuration via Pydantic Settings           |
| `core/database/`| SQLAlchemy async engine, session factory, base models        |
| `core/logger/`  | structlog configuration, request-id propagation              |
| `core/models/`  | ORM model definitions (table schemas)                        |
| `core/utils/`   | Typed exceptions, pagination, and other shared helpers       |
| `core/prompts/` | Prompt template files and loader                             |
| `alembic/`      | Database schema migration history                            |
| `tests/`        | Unit (no I/O) and integration tests                          |
| `scripts/`      | Developer tooling: setup, seed, SQL init                     |
| `docs/`         | Architecture, API conventions, agent contracts               |

---

## Key Design Decisions

### Async-First
All I/O — database queries, HTTP calls, agent tool execution — is async.
SQLAlchemy is used in async mode via `asyncpg`. No blocking calls in hot paths.

### Dependency Injection
FastAPI's `Depends()` system is used for sessions, settings, and auth.
This makes tests trivial: swap real dependencies with in-memory fakes via
`app.dependency_overrides`.

### Typed Exceptions
All application errors subclass `OUTURAIError` with typed `status_code` and
`error_code`. The FastAPI exception handler converts these to consistent
structured JSON responses automatically.

### Settings Validation
Pydantic `BaseSettings` with `model_validator` enforces that production
secrets are real values. If you deploy with `CHANGE_ME` as a secret key,
the app refuses to start.

### Modular Agent Structure
Each agent is isolated in its own sub-package: `agent.py` (class) + `tools.py`
(pure functions). Agents never import from each other — the workflow layer
coordinates them.
