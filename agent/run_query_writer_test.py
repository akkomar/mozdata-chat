#!/usr/bin/env python3
"""
Test script for the query_writer agent.

This script tests the query_writer_tool integration with the root agent
by asking it to generate various BigQuery queries for Mozilla telemetry.

Run with: uv run python run_query_writer_test.py
"""

import asyncio

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from app.agent import root_agent


async def test_query_writer(query: str):
    """Run a single test query and print the response."""
    print(f"\n{'='*60}")
    print(f"QUERY: {query}")
    print('='*60)

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="app", user_id="test_user", session_id="test_session"
    )

    runner = Runner(
        agent=root_agent, app_name="app", session_service=session_service
    )

    async for event in runner.run_async(
        user_id="test_user",
        session_id="test_session",
        new_message=genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=query)]
        ),
    ):
        # Print tool calls for debugging
        if event.get_function_calls():
            for fc in event.get_function_calls():
                print(f"\n[TOOL CALL] {fc.name}")
                if fc.args:
                    args_str = str(fc.args)[:200]
                    print(f"  Args: {args_str}...")

        # Print final response
        if event.is_final_response():
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"\n[RESPONSE]\n{part.text}")


async def main():
    """Run test queries."""
    test_queries = [
        "Write a query to get Firefox Desktop DAU for the last 7 days",
        # Uncomment for additional tests:
        # "How do I calculate MAU by country for Firefox?",
        # "Write a query to analyze shopping events in Firefox",
    ]

    for query in test_queries:
        try:
            await test_query_writer(query)
        except Exception as e:
            print(f"\n[ERROR] {type(e).__name__}: {e}")

    print("\n" + "="*60)
    print("Test complete!")


if __name__ == "__main__":
    asyncio.run(main())
