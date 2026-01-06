# Copyright 2025 Mozilla Corporation
#
# Custom DataHub tools that bypass ADK's schema parser limitations.
# The 'search' and 'get_lineage' MCP tools have circular $ref in their schemas
# that ADK cannot parse. These wrappers call MCP directly with simplified interfaces.

"""Custom DataHub MCP tool wrappers with simplified schemas."""

import json
import os
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


@asynccontextmanager
async def get_datahub_session():
    """Create a DataHub MCP session."""
    token = os.getenv("DATAHUB_API_TOKEN")
    if not token:
        raise ValueError("DATAHUB_API_TOKEN environment variable not set")

    url = f"https://mozilla.acryl.io/integrations/ai/mcp/?token={token}"

    async with streamablehttp_client(url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


async def _call_tool(tool_name: str, arguments: dict) -> dict:
    """Call a DataHub MCP tool and return the result."""
    async with get_datahub_session() as session:
        result = await session.call_tool(tool_name, arguments)
        # Extract text content from the result
        if result.content:
            texts = [c.text for c in result.content if hasattr(c, "text")]
            return {"status": "success", "result": "\n".join(texts)}
        return {"status": "success", "result": "No results returned"}


def _parse_filter_json(filters_json: str) -> dict | None:
    """Parse and validate a filters JSON string.

    Supports the full DataHub filter syntax including AND/OR/NOT combinators.

    Example filters:
        Simple: {"entity_type": ["DATASET"]}
        AND: {"and": [{"entity_type": ["DATASET"]}, {"platform": ["bigquery"]}]}
        OR: {"or": [{"entity_type": ["DATASET"]}, {"entity_type": ["DASHBOARD"]}]}
        NOT: {"not": {"entity_type": ["DATASET"]}}
        Nested: {"and": [{"entity_type": ["DATASET"]}, {"or": [{"platform": ["bigquery"]}, {"platform": ["looker"]}]}]}
    """
    if not filters_json or not filters_json.strip():
        return None

    try:
        filters = json.loads(filters_json)
        if not isinstance(filters, dict):
            return None
        return filters
    except json.JSONDecodeError:
        return None


async def search_datahub(
    query: str,
    filters_json: str,
    limit: int,
    tool_context,
) -> dict:
    """Search across DataHub entities using full-text search with advanced filtering.

    Use this tool to find datasets, tables, dashboards, and other data assets
    in Mozilla's data catalog. Returns matching entities with their URNs and metadata.

    Args:
        query: Search query text to find matching entities (e.g., "firefox telemetry", "main_summary")
        filters_json: Optional JSON string for advanced filtering with AND/OR/NOT support. Examples:
            - Simple type filter: {"entity_type": ["DATASET"]}
            - Simple platform filter: {"platform": ["bigquery"]}
            - AND combinator: {"and": [{"entity_type": ["DATASET"]}, {"platform": ["bigquery"]}]}
            - OR combinator: {"or": [{"entity_type": ["DATASET"]}, {"entity_type": ["DASHBOARD"]}]}
            - NOT combinator: {"not": {"status": ["SOFT_DELETED"]}}
            - Nested: {"and": [{"entity_type": ["DATASET"]}, {"or": [{"platform": ["bigquery"]}, {"platform": ["looker"]}]}]}
            Available filter fields: entity_type (DATASET, DASHBOARD, CHART, DATAFLOW, DATAJOB, GLOSSARYTERM, TAG, CONTAINER), platform, domain, container, env, owner, glossary_term, tag, status.
            Leave empty string for no filtering.
        limit: Maximum number of results to return (1-100, default 10)

    Returns:
        dict: Search results containing matching entities with URNs, names, and descriptions
    """
    arguments = {
        "query": query,
        "num_results": min(max(1, limit or 10), 100),
    }

    filters = _parse_filter_json(filters_json)
    if filters:
        arguments["filters"] = filters

    try:
        result = await _call_tool("search", arguments)
        # Store in session state for query_writer to access
        tool_context.state["datahub_table_info"] = result.get("result", "")
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def get_datahub_lineage(
    urn: str,
    direction: str,
    max_hops: int,
    filters_json: str,
) -> dict:
    """Get upstream or downstream lineage for a DataHub entity with optional filtering.

    Use this tool to understand data dependencies - what datasets feed into
    a table (upstream) or what consumes data from it (downstream).

    Args:
        urn: The DataHub URN of the entity (e.g., "urn:li:dataset:(urn:li:dataPlatform:bigquery,moz-fx-data-shared-prod.telemetry.main_summary,PROD)")
        direction: Lineage direction - "upstream" (data sources) or "downstream" (data consumers)
        max_hops: Maximum number of hops to traverse (1-5, default 1). Higher values show more distant relationships.
        filters_json: Optional JSON string to filter lineage results with AND/OR/NOT support. Examples:
            - Filter by type: {"entity_type": ["DATASET"]}
            - Filter by platform: {"platform": ["bigquery"]}
            - Exclude certain types: {"not": {"entity_type": ["DATAJOB"]}}
            - Combined: {"and": [{"entity_type": ["DATASET"]}, {"platform": ["bigquery"]}]}
            Available filter fields: entity_type, platform, domain, container, env, owner, glossary_term, tag, status.
            Leave empty string for no filtering.

    Returns:
        dict: Lineage information showing connected entities and their relationships
    """
    arguments = {
        "urn": urn,
        "upstream": direction.upper() != "DOWNSTREAM" if direction else True,
        "max_hops": min(max(1, max_hops or 1), 5),
    }

    filters = _parse_filter_json(filters_json)
    if filters:
        arguments["filters"] = filters

    try:
        return await _call_tool("get_lineage", arguments)
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def list_datahub_schema_fields(
    dataset_urn: str,
    keywords: str,
    limit: int,
    offset: int,
    tool_context,
) -> dict:
    """List schema fields for a dataset with optional keyword filtering.

    Use this tool to explore the columns/fields of a dataset, including their
    names, types, and descriptions.

    Args:
        dataset_urn: The DataHub URN of the dataset (e.g., "urn:li:dataset:(urn:li:dataPlatform:bigquery,moz-fx-data-shared-prod.telemetry.main_summary,PROD)")
        keywords: Optional comma-separated keywords to filter fields (e.g., "client_id,submission"). Leave empty for all fields.
        limit: Maximum number of fields to return (1-100, default 50)
        offset: Number of fields to skip for pagination (default 0)

    Returns:
        dict: Schema fields with names, types, descriptions, and other metadata
    """
    arguments = {
        "urn": dataset_urn,
        "limit": min(max(1, limit or 50), 100),
        "offset": max(0, offset or 0),
    }

    if keywords and keywords.strip():
        arguments["keywords"] = [k.strip() for k in keywords.split(",")]

    try:
        result = await _call_tool("list_schema_fields", arguments)
        # Store in session state for query_writer to access
        tool_context.state["datahub_schema_fields"] = result.get("result", "")
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}
