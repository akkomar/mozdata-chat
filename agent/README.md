# Mozdata Assistant Agent

ADK RAG agent for Mozilla data documentation. Provides document retrieval and Q&A capabilities for Mozilla's telemetry, BigQuery datasets, Glean SDK, Looker dashboards, and data pipelines.

Based on [`googleCloudPlatform/agent-starter-pack`](https://github.com/GoogleCloudPlatform/agent-starter-pack) version `0.29.0`.

## Project Structure

This project is organized as follows:

```
mozdata-agent/
├── app/                 # Core application code
│   ├── agent.py         # Main agent logic
│   ├── agent_engine_app.py # Agent Engine application logic
│   └── app_utils/       # App utilities and helpers
├── tests/               # Unit, integration, and load tests
├── Makefile             # Makefile for common commands
├── GEMINI.md            # AI-assisted development guide
└── pyproject.toml       # Project dependencies and configuration
```

> 💡 **Tip:** Use [Gemini CLI](https://github.com/google-gemini/gemini-cli) for AI-assisted development - project context is pre-configured in `GEMINI.md`.

## Requirements

Before you begin, ensure you have:
- **uv**: Python package manager (used for all dependency management in this project) - [Install](https://docs.astral.sh/uv/getting-started/installation/) ([add packages](https://docs.astral.sh/uv/concepts/dependencies/) with `uv add <package>`)
- **Google Cloud SDK**: For GCP services - [Install](https://cloud.google.com/sdk/docs/install)
- **make**: Build automation tool - [Install](https://www.gnu.org/software/make/) (pre-installed on most Unix-based systems)


## Quick Start (Local Testing)

Install required packages and launch the local development environment:

```bash
make install && make playground
```
> **📊 Observability Note:** Agent telemetry (Cloud Trace) is always enabled. Prompt-response logging (GCS, BigQuery, Cloud Logging) is **disabled** locally, **enabled by default** in deployed environments (metadata only - no prompts/responses). See [Monitoring and Observability](#monitoring-and-observability) for details.

## Commands

| Command              | Description                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------- |
| `make install`       | Install all required dependencies using uv                                                  |
| `make playground`    | Launch local development environment for testing agent |
| `make deploy`        | Deploy agent to Agent Engine |
| `make register-gemini-enterprise` | Register deployed agent to Gemini Enterprise ([docs](https://googlecloudplatform.github.io/agent-starter-pack/cli/register_gemini_enterprise.html)) |
| `make test`          | Run unit and integration tests                                                              |
| `make lint`          | Run code quality checks (codespell, ruff, mypy)                                             |
| `make data-ingestion`| Run data ingestion pipeline in the Dev environment                                           |

For full command options and usage, refer to the [Makefile](Makefile).


## Usage

This template follows a "bring your own agent" approach - you focus on your business logic, and the template handles everything else (UI, infrastructure, deployment, monitoring).
1. **Develop:** Edit your agent logic in `app/agent.py`.
2. **Test:** Explore your agent functionality using the local playground with `make playground`. The playground automatically reloads your agent on code changes.
3. **Enhance:** When ready for production, run `uvx agent-starter-pack enhance` to add CI/CD pipelines, Terraform infrastructure, and evaluation notebooks.

The project includes a `GEMINI.md` file that provides context for AI tools like Gemini CLI when asking questions about your template.


## Deployment

You can deploy your agent to a Dev Environment using the following command:

```bash
gcloud config set project <your-dev-project-id>
make deploy
```

After deployment, the script prints a **Console Playground URL** you can use to interact with the deployed agent directly in the GCP console. The current dev deployment playground is at:

https://console.cloud.google.com/vertex-ai/agents/locations/us-central1/agent-engines/5702846855390429184/playground?project=akomar-adk-test

The playground lets you test conversations, inspect traces, and debug tool calls against the live agent without needing the UI.

When ready for production deployment with CI/CD pipelines and Terraform infrastructure, run `uvx agent-starter-pack enhance` to add these capabilities.

## Monitoring and Observability

The application provides two levels of observability:

**1. Agent Telemetry Events (Always Enabled)**
- OpenTelemetry traces and spans exported to **Cloud Trace**
- Tracks agent execution, latency, and system metrics

**2. Prompt-Response Logging (Configurable)**
- GenAI instrumentation captures LLM interactions (tokens, model, timing)
- Exported to **Google Cloud Storage** (JSONL), **BigQuery** (external tables), and **Cloud Logging** (dedicated bucket)

| Environment | Prompt-Response Logging |
|-------------|-------------------------|
| **Local Development** (`make playground`) | ❌ Disabled by default |

**To enable locally:** Set `LOGS_BUCKET_NAME` and `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=NO_CONTENT`.

See the [observability guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/observability.html) for detailed instructions, example queries, and visualization options.

## Mozdata

This project has been customized to ingest Mozilla's data documentation from [docs.telemetry.mozilla.org](https://docs.telemetry.mozilla.org) (source: [github.com/mozilla/data-docs](https://github.com/mozilla/data-docs)) into Vertex AI Search for RAG.

### Changes from Base Template

**Data Ingestion Pipeline** (`data_ingestion/`):
- `components/fetch_docs.py` - Fetches markdown from GitHub (`main` branch), converts to HTML using Python `markdown` library, uploads to GCS. Citation URLs point to live docs site.
- `components/ingest_data.py` - Simplified to use Vertex AI Search native layout parser (no custom embeddings)
- `pipeline.py` - Updated parameters for Mozilla data-docs
- `submit_pipeline.py` - Updated default values for datastore and GCS bucket
- `pyproject.toml` - Replaced `beautifulsoup4` with `markdown>=3.5.0`
- `README.md` - Updated documentation for Mozilla data-docs pipeline

**Infrastructure** (`scripts/`):
- `setup_data_docs_infrastructure.sh` - Creates GCS bucket, Vertex AI Search datastore with layout-based chunking, and Search App

**Agent** (`app/`):
- `agent.py` - Updated instruction and description for Mozilla telemetry/data context
- `retrievers.py` - Simplified to use native Vertex AI Search embeddings

**Build** (root):
- `Makefile` - Added `setup-data-docs` target, updated `data-ingestion` target with Mozilla-specific parameters

### Setup & Usage

```bash
# 1. Set up infrastructure (GCS bucket, Vertex AI Search datastore)
make setup-data-docs

# 2. Run data ingestion pipeline
make data-ingestion

# 3. Test the agent locally
make playground
```

### DataHub Integration

The agent can optionally connect to Mozilla's DataHub (data catalog) via MCP to query dataset metadata, schemas, lineage, and usage patterns.

**Available tools:**
- `search_datahub` - Search for datasets, tables, dashboards with full AND/OR/NOT filter support
- `get_datahub_lineage` - Get upstream/downstream data dependencies with optional filtering
- `list_datahub_schema_fields` - List schema fields/columns for a dataset
- `get_entities` - Get detailed information about datasets by their DataHub URNs
- `get_dataset_queries` - Get SQL queries associated with a dataset

**Advanced filtering examples:**
```json
// Simple filter
{"entity_type": ["DATASET"]}

// AND combinator
{"and": [{"entity_type": ["DATASET"]}, {"platform": ["bigquery"]}]}

// OR combinator
{"or": [{"platform": ["bigquery"]}, {"platform": ["looker"]}]}

// NOT combinator
{"not": {"status": ["SOFT_DELETED"]}}

// Nested filters
{"and": [{"entity_type": ["DATASET"]}, {"or": [{"platform": ["bigquery"]}, {"platform": ["looker"]}]}]}
```

> **Note:** `search_datahub` and `get_datahub_lineage` are custom wrappers that call MCP directly, bypassing ADK's schema parser which cannot handle circular `$ref` references. See [google/adk-python#1055](https://github.com/google/adk-python/issues/1055).

**To enable DataHub:**

1. Get your token from [mozilla.acryl.io](https://mozilla.acryl.io/integrations/ai/mcp/)
2. Set the environment variable:
   ```bash
   export DATAHUB_API_TOKEN="your_token_here"
   ```

**For production:** Use Google Cloud Secret Manager or set the environment variable in your Cloud Run/Agent Engine deployment config.

### Design Decision: Markdown → HTML

The pipeline fetches raw markdown from GitHub instead of rendered HTML from the live site because:
- **Clean content**: 100% useful content vs ~15% (live site has navigation chrome, sidebar, CSS, JS)
- **Smaller files**: ~10KB vs ~150KB per page
- **Faster**: No rate limiting needed for GitHub CDN
- **Structure preserved**: Converted HTML allows Vertex AI Search layout parser to detect headings, lists, tables
