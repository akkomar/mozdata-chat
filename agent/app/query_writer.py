# Copyright 2025 Mozilla Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Query Writer Agent for Mozilla BigQuery.

This module provides a specialized agent for writing BigQuery queries
following Mozilla's best practices. Initial schema data is provided by
the root agent via session state, but this agent also has DataHub tools
to look up additional tables when joins are needed.
"""

import os

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from .query_writer_knowledge import get_query_writer_instruction
from .datahub_tools import search_datahub, list_datahub_schema_fields

# NOTE: BigQuery toolset is disabled because it requires the Agent Engine
# service account to have bigquery.dataViewer permissions on moz-fx-data-shared-prod.
# Instead, we use DataHub for schema validation which doesn't require special permissions.
#
# To enable BigQuery direct access, grant the SA these permissions and uncomment:
# from google.adk.tools.bigquery import BigQueryToolset
# bq_toolset = BigQueryToolset(tool_filter=["get_table_info", "list_table_ids"])

# Build tools list - include DataHub tools for schema validation
datahub_tools = []
if os.getenv("DATAHUB_API_TOKEN"):
    datahub_tools = [search_datahub, list_datahub_schema_fields]

# Create the query writer agent
# Documentation context is provided by root agent via session state.
# This agent uses DataHub tools to validate table schemas and column names.
query_writer_agent = Agent(
    name="query_writer",
    model="gemini-3-flash-preview",
    description="""Specialized agent for writing BigQuery queries for Mozilla telemetry data.
    Use this tool when users ask to:
    - Write BigQuery SQL queries for Mozilla data
    - Calculate DAU, MAU, WAU, or other usage metrics
    - Analyze Firefox/Mozilla product events
    - Query telemetry data with proper filters and best practices

    Before calling this tool, gather documentation context via retrieve_docs.
    This agent will use DataHub to validate table schemas and column names.""",
    instruction=get_query_writer_instruction(),
    # DataHub tools for schema validation
    tools=datahub_tools,
    output_key="generated_query",
)

# Wrap the agent as a tool that can be called by the root agent
query_writer_tool = AgentTool(agent=query_writer_agent)
