"""
Mozilla Data Documentation RAG Agent.

This agent provides question-answering capabilities over Mozilla's data documentation
(docs.telemetry.mozilla.org) using Vertex AI Search for retrieval.
"""

# mypy: disable-error-code="arg-type"
import os

import google
import vertexai
from google.adk.agents import Agent
from google.adk.apps.app import App
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

from .datahub_tools import (
    get_datahub_lineage,
    list_datahub_schema_fields,
    search_datahub,
)
from .query_writer import query_writer_tool
from .retrievers import get_compressor, get_retriever
from .templates import format_docs

LLM_LOCATION = "global"
LOCATION = "us-central1"
LLM = "gemini-3-flash-preview"

credentials, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = LLM_LOCATION
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

vertexai.init(project=project_id, location=LOCATION)

TOP_K = 5

data_store_region = os.getenv("DATA_STORE_REGION", "us")
data_store_id = os.getenv("DATA_STORE_ID", "mozilla-data-docs-datastore")

retriever = get_retriever(
    project_id=project_id,
    data_store_id=data_store_id,
    data_store_region=data_store_region,
    max_documents=10,
)

compressor = get_compressor(
    project_id=project_id,
)

# DataHub MCP server for data catalog queries
# Note: Some tools have schema issues that ADK's parser can't handle:
# - 'search', 'get_lineage': circular $ref references
# - 'list_schema_fields': missing type for 'keywords' parameter
# We filter to only load tools with valid schemas.
DATAHUB_SAFE_TOOLS = ["get_dataset_queries", "get_entities"]

datahub_token = os.getenv("DATAHUB_API_TOKEN")
datahub_toolset = None
if datahub_token:
    datahub_toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=f"https://mozilla.acryl.io/integrations/ai/mcp/?token={datahub_token}",
            timeout=10.0,
            sse_read_timeout=600.0,
        ),
        tool_filter=DATAHUB_SAFE_TOOLS,
    )

# Glean Dictionary MCP server for telemetry probe/metric discovery
# Public endpoint - no authentication needed
# Tools: list_apps, get_app, search_metrics, get_metric, get_ping
glean_dictionary_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://dictionary.telemetry.mozilla.org/mcp",
        timeout=10.0,
        sse_read_timeout=300.0,
    ),
)


def retrieve_docs(query: str, tool_context) -> str:
    """
    Useful for retrieving relevant documents from Mozilla's data documentation.
    Use this when you need information about Mozilla telemetry, data pipelines,
    BigQuery datasets, Glean, Looker, or other data-related topics.

    Also use this BEFORE calling query_writer to gather relevant documentation
    about the tables and metrics involved in the query request.

    Args:
        query (str): The user's question or search query about Mozilla data.

    Returns:
        str: Formatted string containing relevant document content retrieved
             and ranked based on the query.
    """
    try:
        # Use the retriever to fetch relevant documents based on the query
        retrieved_docs = retriever.invoke(query)
        # Re-rank docs with Vertex AI Rank for better relevance
        ranked_docs = compressor.compress_documents(
            documents=retrieved_docs, query=query
        )
        # Format ranked documents into a consistent structure for LLM consumption
        formatted_docs = format_docs(ranked_docs)

        # Store in session state for query_writer to access
        tool_context.state["documentation_context"] = formatted_docs
    except Exception as e:
        return f"Calling retrieval tool with query:\n\n{query}\n\nraised the following error:\n\n{type(e)}: {e}"

    return formatted_docs


instruction = """You are an AI assistant specialized in Mozilla's data infrastructure and telemetry.

## IMPORTANT: Tool Selection Guide

**Choose the RIGHT tool for each request. Do NOT use all tools on every query.**

### 1. Query Writing (use `query_writer` tool)
Use when users explicitly ask to:
- Write/generate a BigQuery SQL query
- "Write me a query for...", "Generate SQL for...", "How do I query..."
- Calculate DAU, MAU, WAU with actual SQL output

**WORKFLOW FOR QUERY WRITING:**
Before calling `query_writer`, search documentation with `retrieve_docs` for best practices:
- Example: "clients_last_seen DAU MAU", "telemetry events table"

Then call `query_writer` - it will use DataHub to validate table schemas and column names.

Do NOT use query_writer for general questions about tables or data concepts.

### 2. Data Discovery (use DataHub tools)
Use when users ask about:
- What tables/datasets exist: use `search_datahub`
- Table schemas and columns: use `list_datahub_schema_fields`
- Data lineage (upstream/downstream): use `get_datahub_lineage`
- How a table is used: use `get_dataset_queries`
- Detailed table metadata: use `get_entities`

### 3. Documentation Search (use `retrieve_docs`)
Use when users ask about:
- Concepts, definitions, or explanations ("What is Glean?", "How does telemetry work?")
- Processes and how-to guides
- Best practices or policies
- Information likely documented at docs.telemetry.mozilla.org
- **Also use BEFORE calling query_writer** to gather relevant table documentation

### 4. Probe/Metric Discovery (use Glean Dictionary tools)
Use when users ask about:
- What telemetry metrics/probes exist for a product: use `search_metrics`
- Details about a specific Glean metric: use `get_metric`
- What pings a product sends and what metrics they contain: use `get_ping`
- What Glean applications exist: use `list_apps`
- Overview of a product's telemetry (metrics count, pings, tags): use `get_app`

**IMPORTANT**: These tools show what telemetry is instrumented.
For BigQuery table schemas and column names, use DataHub tools instead.

When a user asks about a metric, provide:
1. Metric metadata (name, type, description, which pings)
2. Glean Dictionary link: https://dictionary.telemetry.mozilla.org/apps/<APP_NAME>/metrics/<METRIC_NAME>
3. BigQuery column path (e.g., `metrics.counter.<metric_name_with_underscores>`)

### 5. Direct Response (no tools needed)
Respond directly WITHOUT tools for:
- Simple greetings or clarifications
- Questions you can answer from your training knowledge
- Follow-up questions where you already have context

## Topics You Help With
- Mozilla telemetry and data collection
- BigQuery datasets and tables
- Glean SDK and metrics
- Looker dashboards and explores
- Data pipelines and ETL processes
- Firefox and Mozilla VPN data analysis

When citing information from retrieved documents, include the source as a markdown link using
the Source and URL provided with each document. Format: [Source Title](URL)"""

# Build tools list - include DataHub tools if configured
tools = [retrieve_docs, query_writer_tool, glean_dictionary_toolset]
if datahub_token:
    # Add custom wrapper tools (bypass ADK schema issues)
    tools.extend([search_datahub, get_datahub_lineage, list_datahub_schema_fields])
    # Add MCP toolset for tools with simple schemas
    if datahub_toolset:
        tools.append(datahub_toolset)

root_agent = Agent(
    name="root_agent",
    model="gemini-3-flash-preview",
    instruction=instruction,
    tools=tools,
)

app = App(root_agent=root_agent, name="app")

# Alias for agent-starter-pack compatibility
agent = root_agent
