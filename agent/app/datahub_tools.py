# Copyright 2025 Mozilla Corporation
#
# Custom DataHub tools that bypass ADK's schema parser limitations.
# The 'search' and 'get_lineage' MCP tools have circular $ref in their schemas
# that ADK cannot parse. These wrappers call MCP directly with simplified interfaces.

"""Custom DataHub MCP tool wrappers with simplified schemas."""

import json
import os
import re
from contextlib import asynccontextmanager
from difflib import SequenceMatcher

import sqlglot
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


def _extract_tables_and_columns(sql: str) -> dict:
    """Extract table and column references from SQL using sqlglot.

    Returns:
        dict with:
        - tables: set of table names found
        - columns: dict mapping table names to sets of column names
        - all_columns: set of all column names (for tables we couldn't resolve)
    """
    try:
        parsed = sqlglot.parse_one(sql, dialect="bigquery")
    except Exception as e:
        return {"error": f"Failed to parse SQL: {e}", "tables": set(), "columns": {}, "all_columns": set()}

    tables = set()
    table_aliases = {}  # alias -> full table name
    columns_by_table: dict[str, set] = {}
    all_columns: set[str] = set()

    # Extract tables and their aliases
    for table in parsed.find_all(sqlglot.exp.Table):
        # Get full table name (may include project.dataset.table)
        table_name = table.name
        if table.db:
            table_name = f"{table.db}.{table_name}"
        if table.catalog:
            table_name = f"{table.catalog}.{table_name}"

        tables.add(table_name)

        # Track aliases
        if table.alias:
            table_aliases[table.alias] = table_name

    # Extract columns
    for column in parsed.find_all(sqlglot.exp.Column):
        col_name = column.name
        all_columns.add(col_name)

        # Try to determine which table this column belongs to
        table_ref = column.table
        if table_ref:
            # Resolve alias to full table name
            resolved_table = table_aliases.get(table_ref, table_ref)
            if resolved_table not in columns_by_table:
                columns_by_table[resolved_table] = set()
            columns_by_table[resolved_table].add(col_name)
        else:
            # Column without explicit table reference - add to all tables
            # (or we could add to a special "unresolved" bucket)
            for t in tables:
                if t not in columns_by_table:
                    columns_by_table[t] = set()
                columns_by_table[t].add(col_name)

    return {
        "tables": tables,
        "columns": columns_by_table,
        "all_columns": all_columns,
    }


def _find_similar_columns(target: str, schema_columns: set, top_n: int = 3) -> list:
    """Find similar column names using string similarity."""
    scored = []
    target_lower = target.lower()
    for col in schema_columns:
        # Use SequenceMatcher for similarity
        ratio = SequenceMatcher(None, target_lower, col.lower()).ratio()
        # Boost exact substring matches
        if target_lower in col.lower() or col.lower() in target_lower:
            ratio += 0.3
        scored.append((col, ratio))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [col for col, _ in scored[:top_n] if scored[0][1] > 0.3]


def _normalize_table_name(table_name: str) -> str:
    """Normalize table name for comparison (lowercase, handle aliases)."""
    # Remove project prefix if present (moz-fx-data-shared-prod)
    parts = table_name.split(".")
    if len(parts) >= 2:
        # Return dataset.table format
        return ".".join(parts[-2:]).lower()
    return table_name.lower()


def _find_table_urn(search_result_text: str, table_name: str) -> str | None:
    """Extract the best matching URN from search results."""
    # Parse the search result to find URNs
    # Look for URN patterns in the result
    urn_pattern = r'urn:li:dataset:\([^)]+\)'
    urns = re.findall(urn_pattern, search_result_text)

    if not urns:
        return None

    # Find best match based on table name
    normalized_target = _normalize_table_name(table_name)
    for urn in urns:
        if normalized_target in urn.lower():
            return urn

    # Return first URN if no exact match
    return urns[0] if urns else None


async def validate_query_columns(
    sql_query: str,
    tool_context,
) -> dict:
    """Validate that all columns in a SQL query exist in the referenced tables.

    Use this tool AFTER generating a query to verify all column names are correct.
    This helps catch errors like using 'submission_date' when the table has 'submission_timestamp'.

    Args:
        sql_query: The SQL query to validate

    Returns:
        dict with:
        - valid: bool - True if all columns exist in their tables
        - errors: list - Column errors with suggestions for correct column names
        - tables_checked: list - Tables that were validated against DataHub
        - message: str - Summary of validation result
    """
    # Parse the SQL to extract tables and columns
    parsed = _extract_tables_and_columns(sql_query)

    if parsed.get("error"):
        return {
            "valid": False,
            "errors": [{"error": parsed["error"]}],
            "tables_checked": [],
            "message": f"Failed to parse SQL: {parsed['error']}",
        }

    tables = parsed["tables"]
    columns_by_table = parsed["columns"]

    if not tables:
        return {
            "valid": True,
            "errors": [],
            "tables_checked": [],
            "message": "No tables found in query to validate.",
        }

    errors = []
    tables_checked = []

    for table_name in tables:
        try:
            # Search for the table in DataHub
            search_args = {
                "query": table_name,
                "filters": {
                    "and": [
                        {"entity_type": ["DATASET"]},
                        {"platform": ["bigquery"]},
                    ]
                },
                "num_results": 5,
            }
            search_result = await _call_tool("search", search_args)
            result_text = search_result.get("result", "")

            # Find the URN for this table
            urn = _find_table_urn(result_text, table_name)
            if not urn:
                errors.append({
                    "table": table_name,
                    "error": f"Could not find table '{table_name}' in DataHub",
                    "suggestions": [],
                })
                continue

            # Get the schema for this table
            schema_args = {"urn": urn, "limit": 200, "offset": 0}
            schema_result = await _call_tool("list_schema_fields", schema_args)
            schema_text = schema_result.get("result", "")

            # Extract column names from schema result
            # The schema result contains field paths like "fieldPath": "column_name"
            schema_columns: set[str] = set()
            # Look for fieldPath patterns in the result
            field_pattern = r'"fieldPath":\s*"([^"]+)"'
            for match in re.finditer(field_pattern, schema_text):
                field_path = match.group(1)
                # Handle nested fields (e.g., "struct.field")
                # Add both the full path and the leaf name
                schema_columns.add(field_path)
                if "." in field_path:
                    schema_columns.add(field_path.split(".")[-1])

            if not schema_columns:
                # Try alternative parsing - look for "name" fields
                name_pattern = r'"name":\s*"([^"]+)"'
                for match in re.finditer(name_pattern, schema_text):
                    schema_columns.add(match.group(1))

            tables_checked.append(table_name)

            # Validate columns for this table
            table_columns = columns_by_table.get(table_name, set())
            for col in table_columns:
                # Check if column exists (case-insensitive)
                col_lower = col.lower()
                schema_lower = {c.lower() for c in schema_columns}

                if col_lower not in schema_lower:
                    suggestions = _find_similar_columns(col, schema_columns)
                    errors.append({
                        "column": col,
                        "table": table_name,
                        "error": f"Column '{col}' not found in table '{table_name}'",
                        "suggestions": suggestions,
                    })

        except Exception as e:
            errors.append({
                "table": table_name,
                "error": f"Error validating table '{table_name}': {e}",
                "suggestions": [],
            })

    # Build result message
    if not errors:
        message = f"Query validation PASSED. All columns verified in {len(tables_checked)} table(s): {', '.join(tables_checked)}"
        valid = True
    else:
        error_msgs = []
        for err in errors:
            if "column" in err:
                sugg = f" Did you mean: {', '.join(err['suggestions'])}" if err.get("suggestions") else ""
                error_msgs.append(f"- {err['error']}.{sugg}")
            else:
                error_msgs.append(f"- {err['error']}")
        message = f"Query validation FAILED with {len(errors)} error(s):\n" + "\n".join(error_msgs)
        valid = False

    return {
        "valid": valid,
        "errors": errors,
        "tables_checked": tables_checked,
        "message": message,
    }
