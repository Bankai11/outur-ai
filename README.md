<div align="center">
  <h1>OUTUR AI</h1>
  <p><b>AI-powered outbound outreach automation platform</b></p>

  [![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-00a393.svg)](https://fastapi.tiangolo.com/)
  [![Redis](https://img.shields.io/badge/Redis-5.3+-dc382d.svg)](https://redis.io/)
  [![Docker](https://img.shields.io/badge/Docker-Compose-2496ed.svg)](https://www.docker.com/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
  [![Status](https://img.shields.io/badge/Status-Active-success.svg)]()
</div>

## Overview

Outur AI is an advanced, multi-agent platform designed to completely automate the B2B business development process. From initial lead discovery to personalized outreach, Outur AI acts as an autonomous sales development representative that never sleeps. 

The platform utilizes a sophisticated pipeline of AI agents—including a Scout, Researcher, and Scorer—to hunt down high-value companies and uncover key decision-makers. Instead of relying on generic email blasts, Outur AI generates hyper-personalized outreach messages based on deep research into a company's hiring signals, growth indicators, and public pain points.

Under the hood, Outur AI is built for scale. It leverages a robust architecture featuring a FastAPI backend, asynchronous PostgreSQL persistence, and Redis-backed ARQ queue workers. This allows the platform to process hundreds of leads in the background reliably, ensuring that research and email drafting happen concurrently without blocking the main application.

Outur AI is built for modern sales teams, recruiters, startup founders, and marketing agencies who need to scale their outbound efforts without sacrificing the quality and personalization of their messaging.

---

## Key Features

| Feature                | Description                         |
| ---------------------- | ----------------------------------- |
| 🤖 **AI Personalization**  | Generate tailored outreach messages |
| 📰 **Research Agent**      | Enrich company context              |
| 📬 **Campaign Automation** | Schedule and send outreach          |
| ⚡ **Redis + ARQ Queue**    | Background processing               |
| 📊 **Analytics Dashboard** | Track campaign performance          |
| 🔒 **Secure API**          | Token-based authentication          |

---

## System Architecture

```mermaid
flowchart TB
    Client([Client / Dashboard]) --> API[FastAPI Backend]
    
    subgraph Core Services
        API --> DB[(PostgreSQL)]
        API --> Queue[Redis Queue]
    end
    
    subgraph Worker Pool
        Queue --> Worker[ARQ Worker]
    end
    
    subgraph Multi-Agent Pipeline
        Worker --> Scout[Scout Agent\nLead Discovery]
        Worker --> Researcher[Researcher Agent\nContact Enrichment]
        Worker --> Scorer[Scorer Agent\nLead Qualification]
        Worker --> Campaign[Campaign Manager\nOutreach Generation]
    end
    
    Scout -.-> LLM[Google Gemini / LLM]
    Researcher -.-> LLM
    Scorer -.-> LLM
    Campaign -.-> LLM
```

---

## Screenshots

<div align="center">
  <img src="https://via.placeholder.com/800x400.png?text=Dashboard+Overview" alt="Dashboard Overview" width="800"/>
  <br/>
  <em>Main Analytics Dashboard</em>
</div>

<br/>

<div align="center">
  <img src="https://via.placeholder.com/800x400.png?text=Campaign+Manager+View" alt="Campaign Manager View" width="800"/>
  <br/>
  <em>Campaign Manager & Lead Scoring</em>
</div>

---

## Tech Stack

| Layer            | Technology                   |
| ---------------- | ---------------------------- |
| Backend          | FastAPI                      |
| Queue            | Redis + ARQ                  |
| Database         | PostgreSQL                   |
| AI               | Google Gemini / LLM APIs     |
| Containerization | Docker Compose               |
| Language         | Python 3.12+                 |

---

## Quick Start (Zero-Configuration)

The fastest way to get started with Outur AI is using our new CLI. You don't need to edit any configuration files manually!

```bash
# 1. Clone the repository
git clone https://github.com/Bankai11/outur-ai.git
cd outur-ai

# 2. Install dependencies using uv
uv sync

# 3. Run the setup wizard!
uv run python -m cli.main init
```

The `init` wizard will guide you step-by-step. It will check your system, ask for your API keys (Gemini, Tavily, etc.), and ask a few simple questions about your business to set up your AI Sales Brain.

---

## How to Use the CLI

Once initialized, you can manage your entire outbound operation directly from the terminal.

**1. Launch a Campaign**
Just describe what you want in plain English!
```bash
uv run python -m cli.main run
```
*Example: "Find me 50 HR Managers at mid-sized SaaS companies in London who are actively hiring."*

**2. Review Drafts**
Check the emails the AI wrote for you before sending them:
```bash
uv run python -m cli.main review
```

**3. Send Emails**
Send all the drafts you just approved:
```bash
uv run python -m cli.main send
```

**4. Check System Health**
Having issues? Run the doctor to verify your setup:
```bash
uv run python -m cli.main doctor
```

**5. Update Settings**
View or change your business profile and API keys:
```bash
uv run python -m cli.main config
```

---

## API Example

Launch a new discovery campaign via the REST API:

```bash
curl -X POST "http://localhost:8000/api/v1/campaigns" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -d '{
           "industry": "Artificial Intelligence",
           "country": "United States",
           "limit": 10
         }'
```

---

## Roadmap

- [x] Phase 1: Scout Agent & Database Architecture
- [x] Phase 2: Redis + ARQ Background Queue Setup
- [ ] Phase 3: Enrichment & Lead Scoring Agents
- [ ] Phase 4: Campaign Manager & Personalized Outreach
- [ ] Phase 5: CRM Analytics Dashboard
- [ ] Phase 6: Fully Autonomous End-to-End Pipeline

---

## Troubleshooting

**Redis connection errors**
Ensure the Redis container is running (`docker compose ps`). Check that `REDIS_URL` in your `.env` correctly points to `redis://localhost:6379/0` (or `redis://redis:6379/0` if inside Docker).

**Worker not processing jobs**
Make sure the ARQ worker process is running. If running locally, ensure you started it via `uv run arq core.queue.worker.WorkerSettings`. Check the worker logs for any unhandled exceptions.

**Docker build failures**
If `hatchling` fails to build due to a missing `README.md`, ensure your `Dockerfile` copies `README.md` during the dependency installation stage (`COPY pyproject.toml uv.lock* README.md ./`).

**Missing environment variables**
If you see validation errors on startup, double-check that your `.env` file exists in the root directory and contains all required variables, particularly `GEMINI_API_KEY` and `DATABASE_URL`.

---

## Contributing

We welcome contributions to Outur AI! To get started:

1. Fork the repository.
2. Create a new feature branch (`git checkout -b feat/amazing-feature`).
3. Ensure you write tests for any new functionality (TDD preferred).
4. Run the test suite and linters (`uv run pytest` and `uv run ruff check .`).
5. Commit your changes following Conventional Commits.
6. Push to your branch and open a Pull Request against `develop`.

---

<div align="center">
  <p>Built with ❤️ by the Outur AI team</p>
</div>
