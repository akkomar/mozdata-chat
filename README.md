# Mozdata Chat

> **Note:** This is an experimental proof of concept, do not use.

Chat interface for exploring Mozilla's data ecosystem. Ask questions about BigQuery tables, Glean metrics, Looker dashboards, or telemetry pipelines and get answers grounded in [docs.telemetry.mozilla.org](https://docs.telemetry.mozilla.org) and live metadata from [DataHub](https://mozilla.acryl.io).

## Why This Exists

Mozilla's data documentation is scattered and dense. This tool lets you ask questions in plain English instead of hunting through docs or clicking around DataHub.

Built with Google's [Agent Development Kit](https://google.github.io/adk-docs/) and deployed on Vertex AI Agent Engine.

## Architecture

```
Browser → Next.js (Firebase Auth) → Python Proxy → Vertex AI Agent Engine
                                                            ↓
                                         ADK Agent with RAG, DataHub MCP, BigQuery tools
```

## Quick Start

**Prerequisites:** Node.js 18+, Python 3.10+ with `uv`, `gcloud` CLI

```bash
# Run the UI (connects to deployed agent)
cd ui
cp proxy/.env.example proxy/.env   # add your agent endpoint
pnpm install && pnpm dev           # http://localhost:3000

# Or run the agent locally
cd agent
make install && make playground    # http://localhost:8501
```

Sign in with your @mozilla.com account.

## Project Layout

| Directory | What's There |
|-----------|--------------|
| `agent/`  | ADK agent, DataHub tools, RAG ingestion pipeline. See [agent/README.md](./agent/README.md) |
| `ui/`     | Next.js chat UI, FastAPI proxy, Terraform. See [ui/README.md](./ui/README.md) |

## Security

Auth is Firebase + Identity Platform, restricted to @mozilla.com accounts. The proxy verifies ID tokens on every request.

## Questions?

Internal Mozilla project. Ping the Data Engineering team.
