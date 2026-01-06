"""
Agent Engine Proxy Server

A FastAPI server that proxies AG-UI protocol requests to a deployed
Vertex AI Agent Engine, translating events between the two protocols.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, AsyncIterator

import vertexai
import firebase_admin
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from firebase_admin import auth as firebase_auth

load_dotenv()

# Initialize Firebase Admin SDK
# Must specify the project ID that issued the tokens
FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID")
if not FIREBASE_PROJECT_ID:
    raise ValueError("FIREBASE_PROJECT_ID environment variable is required")
firebase_admin.initialize_app(options={
    'projectId': FIREBASE_PROJECT_ID,
})

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Agent Engine configuration (all required - no defaults)
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("VERTEX_LOCATION", "us-central1")
RESOURCE_ID = os.environ.get("AGENT_ENGINE_RESOURCE_ID")

if not PROJECT_ID or not RESOURCE_ID:
    raise ValueError(
        "GOOGLE_CLOUD_PROJECT and AGENT_ENGINE_RESOURCE_ID environment variables are required. "
        "Copy .env.example to .env and fill in your values."
    )

# Initialize Vertex AI client
logger.info(f"Initializing Vertex AI client for project {PROJECT_ID}, location {LOCATION}")
client = vertexai.Client(project=PROJECT_ID, location=LOCATION)
agent = client.agent_engines.get(
    name=f"projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{RESOURCE_ID}"
)
logger.info(f"Connected to Agent Engine: {RESOURCE_ID}")

app = FastAPI(title="Agent Engine Proxy")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def verify_firebase_token(request: Request) -> dict:
    """
    Verify Firebase ID token and check that user is from @mozilla.com domain.

    Returns the decoded token if valid, raises HTTPException otherwise.
    """
    # Skip token verification for health check endpoint
    if request.url.path == "/health":
        return {}

    # Get Firebase token from custom header (avoiding conflicts with HttpAgent)
    auth_header = request.headers.get("x-firebase-token")

    if not auth_header or not auth_header.startswith("Bearer "):
        logger.warning(f"Missing or invalid x-firebase-token header: {auth_header}")
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid authentication token"
        )

    # Extract token and strip any whitespace
    token = auth_header.split("Bearer ", 1)[1].strip()

    logger.info(f"Token received, length: {len(token)}")

    try:
        # Verify the Firebase ID token
        decoded_token = firebase_auth.verify_id_token(token)

        # Check email domain
        email = decoded_token.get("email", "")
        if not email.endswith("@mozilla.com"):
            logger.warning(f"Non-Mozilla user attempted access: {email}")
            raise HTTPException(
                status_code=403,
                detail="Access restricted to Mozilla employees only"
            )

        logger.info(f"Authenticated request from: {email}")
        return decoded_token

    except firebase_auth.InvalidIdTokenError as e:
        logger.error(f"Invalid Firebase token: {e}")
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=401,
            detail="Authentication failed"
        )


def create_sse_event(event_type: str, **kwargs: Any) -> str:
    """Create an SSE-formatted AG-UI protocol event."""
    event_data = {"type": event_type, **kwargs}
    json_str = json.dumps(event_data)
    # SSE format: "data: {json}\n\n"
    return f"data: {json_str}\n\n"


def extract_parts(event: Any) -> list:
    """Extract parts from an Agent Engine event (dict or Pydantic model)."""
    if isinstance(event, dict):
        content = event.get("content")
        if content and isinstance(content, dict):
            return content.get("parts", [])
    else:
        if hasattr(event, "content") and event.content:
            return getattr(event.content, "parts", []) or []
    return []


def get_part_attr(part: Any, attr: str, default: Any = None) -> Any:
    """Get attribute from a part (dict or Pydantic model)."""
    if isinstance(part, dict):
        return part.get(attr, default)
    return getattr(part, attr, default)


def _summarize_args(args: dict) -> str:
    """Create a compact summary of tool arguments for display."""
    if not args:
        return ""

    # Extract key info based on common patterns
    summary_parts = []

    # Common query/search arguments
    if "query" in args:
        q = args["query"]
        if len(q) > 50:
            q = q[:50] + "..."
        summary_parts.append(f'"{q}"')

    # Table/dataset arguments
    if "table_id" in args:
        summary_parts.append(f"table: {args['table_id']}")
    if "dataset_id" in args:
        summary_parts.append(f"dataset: {args['dataset_id']}")
    if "urn" in args:
        # Shorten DataHub URNs
        urn = args["urn"]
        if "urn:li:dataset:" in urn:
            # Extract just the table name part
            parts = urn.split(",")
            if len(parts) >= 2:
                summary_parts.append(parts[1].split(")")[0])
            else:
                summary_parts.append(urn[-40:] if len(urn) > 40 else urn)

    # If we found key args, format them
    if summary_parts:
        return " → " + ", ".join(summary_parts)

    # Fallback: show first string arg if short
    for v in args.values():
        if isinstance(v, str) and len(v) < 50:
            return f' → "{v}"'

    return ""


async def translate_agent_events(
    message: str,
    user_id: str,
    thread_id: str,
    run_id: str,
) -> AsyncIterator[str]:
    """
    Stream events from Agent Engine and translate to AG-UI protocol.

    Yields SSE-formatted event strings including tool calls for visibility.
    Uses a background heartbeat task to keep connection alive during long-running queries.
    """
    import asyncio

    message_id = str(uuid.uuid4())
    tool_call_counter = 0  # For generating unique tool call IDs

    # Emit RUN_STARTED event
    yield create_sse_event("RUN_STARTED", threadId=thread_id, runId=run_id)

    # Emit TEXT_MESSAGE_START event
    yield create_sse_event(
        "TEXT_MESSAGE_START",
        messageId=message_id,
        role="assistant",
    )

    # Use a queue to handle both agent events and heartbeats
    event_queue: asyncio.Queue = asyncio.Queue()
    stop_heartbeat = asyncio.Event()

    async def heartbeat_task():
        """Send heartbeat every 5 seconds to keep connection alive."""
        while not stop_heartbeat.is_set():
            await asyncio.sleep(5)
            if not stop_heartbeat.is_set():
                await event_queue.put(("heartbeat", None))

    async def agent_stream_task():
        """Stream events from Agent Engine into the queue."""
        try:
            async for event in agent.async_stream_query(
                message=message,
                user_id=user_id,
            ):
                await event_queue.put(("event", event))
        except Exception as e:
            await event_queue.put(("error", e))
        finally:
            await event_queue.put(("done", None))

    # Start both tasks
    heartbeat = asyncio.create_task(heartbeat_task())
    agent_stream = asyncio.create_task(agent_stream_task())

    try:
        while True:
            event_type, event_data = await event_queue.get()

            if event_type == "heartbeat":
                yield ": heartbeat\n\n"
                continue

            if event_type == "done":
                break

            if event_type == "error":
                logger.error(f"Error streaming from Agent Engine: {event_data}")
                yield create_sse_event(
                    "TEXT_MESSAGE_CONTENT",
                    messageId=message_id,
                    delta=f"Error: {str(event_data)}",
                )
                break

            # Process agent event - extract parts
            event = event_data
            parts = extract_parts(event)

            for part in parts:
                # Check for text content
                text = get_part_attr(part, "text")
                if text:
                    yield create_sse_event(
                        "TEXT_MESSAGE_CONTENT",
                        messageId=message_id,
                        delta=text,
                    )
                    continue

                # Check for function call (tool invocation)
                # Emit as AG-UI TOOL_CALL events for proper UI rendering
                function_call = get_part_attr(part, "function_call")
                if function_call:
                    func_name = get_part_attr(function_call, "name", "unknown_tool")
                    func_args = get_part_attr(function_call, "args", {})
                    tool_call_counter += 1
                    tool_call_id = f"tc_{run_id}_{tool_call_counter}"

                    # Emit TOOL_CALL_START
                    yield create_sse_event(
                        "TOOL_CALL_START",
                        toolCallId=tool_call_id,
                        toolCallName=func_name,
                    )

                    # Emit TOOL_CALL_ARGS with summarized args
                    args_summary = _summarize_args(func_args)
                    if args_summary:
                        yield create_sse_event(
                            "TOOL_CALL_ARGS",
                            toolCallId=tool_call_id,
                            delta=args_summary,
                        )

                    # Emit TOOL_CALL_END immediately (we don't wait for response)
                    yield create_sse_event(
                        "TOOL_CALL_END",
                        toolCallId=tool_call_id,
                    )
                    continue

                # Check for function response (tool result) - skip display
                # Tool results are processed by the agent and summarized in text
                function_response = get_part_attr(part, "function_response")
                if function_response:
                    # Don't display raw results - agent will summarize
                    continue

    finally:
        # Stop heartbeat task
        stop_heartbeat.set()
        heartbeat.cancel()
        try:
            await heartbeat
        except asyncio.CancelledError:
            pass

    # Emit TEXT_MESSAGE_END event
    yield create_sse_event(
        "TEXT_MESSAGE_END",
        messageId=message_id,
    )

    # Emit RUN_FINISHED event
    yield create_sse_event("RUN_FINISHED", threadId=thread_id, runId=run_id)


@app.post("/")
async def handle_agent_request(
    request: Request,
    user_token: dict = Depends(verify_firebase_token)
):
    """
    Handle AG-UI protocol requests and proxy to Agent Engine.

    Requires valid Firebase ID token for @mozilla.com users.

    Expects a JSON body with:
    - messages: List of conversation messages
    - threadId: Conversation thread ID (optional)
    - runId: Run ID (optional)
    """
    try:
        body = await request.json()

        # Extract the latest user message
        messages = body.get("messages", [])
        latest_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    latest_message = content
                elif isinstance(content, list):
                    # Handle structured content
                    for part in content:
                        if isinstance(part, dict) and part.get("text"):
                            latest_message = part["text"]
                            break
                break

        if not latest_message:
            latest_message = "Hello"

        thread_id = body.get("threadId", str(uuid.uuid4()))
        run_id = body.get("runId", str(uuid.uuid4()))

        # Use authenticated user's email as user_id
        user_id = user_token.get("email", "default_user")

        logger.info(f"Processing request from {user_id}: {latest_message[:80]}{'...' if len(latest_message) > 80 else ''}")

        return StreamingResponse(
            translate_agent_events(
                message=latest_message,
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    except Exception as e:
        logger.error(f"Error handling request: {e}")
        raise


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "agent_engine": RESOURCE_ID}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting Agent Engine Proxy on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
