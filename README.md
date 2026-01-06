# Mozdata Chat

A full-stack AI assistant for exploring Mozilla's data ecosystem, built with Google's Agent Development Kit (ADK) and a CopilotKit-based chat interface.

## Overview

Mozdata Chat helps Mozilla employees explore and understand:
- BigQuery datasets and tables
- Glean SDK metrics and telemetry
- Looker dashboards and explores
- Data pipelines and ETL processes
- Mozilla data documentation

The system consists of two main components:
- **Agent** (`agent/`): Backend AI agent deployed on Vertex AI Agent Engine
- **UI** (`ui/`): CopilotKit chat interface with Firebase Authentication

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User (Browser)                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ui/ - Chat Interface                                 │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐    │
│  │   Next.js UI    │───▶│  /api/copilotkit │───▶│   Python Proxy      │    │
│  │   + Firebase    │    │   (AG-UI Proto)  │    │   (Token Verify)    │    │
│  │   Auth          │    │                  │    │                     │    │
│  └─────────────────┘    └──────────────────┘    └──────────┬──────────┘    │
└─────────────────────────────────────────────────────────────┼───────────────┘
                                                              │
                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    agent/ - Vertex AI Agent Engine                           │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        Mozdata Agent (ADK)                          │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │    │
│  │  │  DataHub    │  │  BigQuery   │  │  RAG (Data  │  │  Query    │  │    │
│  │  │  MCP Server │  │  Toolset    │  │  Docs)      │  │  Writer   │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Getting Started

### Prerequisites

- Google Cloud account with access to the agent project
- `gcloud` CLI installed and authenticated
- Node.js 18+ (for UI)
- Python 3.10+ with `uv` (for agent)

### Quick Start (Development)

1. **Deploy or connect to the Agent**:
   ```bash
   cd agent
   # See agent/README.md for deployment instructions
   ```

2. **Run the UI locally**:
   ```bash
   cd ui
   cp proxy/.env.example proxy/.env
   # Edit proxy/.env with your Agent Engine configuration

   pnpm install
   pnpm dev
   ```

3. **Open http://localhost:3000** and sign in with your @mozilla.com account.

## Project Structure

```
mozdata-chat/
├── agent/                    # Backend AI agent (ADK)
│   ├── app/                  # Agent code
│   │   ├── agent.py          # Root agent definition
│   │   ├── query_writer.py   # SQL query generation sub-agent
│   │   └── tools/            # Custom tools
│   ├── data_ingestion/       # RAG pipeline for data-docs
│   └── README.md             # Agent setup & deployment guide
│
├── ui/                       # Frontend chat interface
│   ├── src/                  # Next.js application
│   ├── proxy/                # Python proxy for Agent Engine
│   ├── tf/                   # Terraform for UI deployment
│   └── README.md             # UI setup & deployment guide
│
└── README.md                 # This file
```

## Documentation

- **Agent Setup**: See [agent/README.md](./agent/README.md)
- **UI Deployment**: See [ui/README.md](./ui/README.md) and [ui/DEPLOY.md](./ui/DEPLOY.md)
- **Mozilla Data Docs**: https://docs.telemetry.mozilla.org

## Security

- **Authentication**: Firebase Authentication restricted to @mozilla.com accounts
- **Authorization**: Identity Platform blocking functions prevent non-Mozilla sign-ups
- **Token Verification**: Backend proxy validates Firebase ID tokens on every request

## Contributing

This is an internal Mozilla project. For questions or contributions, contact the Data Engineering team.
