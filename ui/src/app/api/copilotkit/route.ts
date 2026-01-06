import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";
import { NextRequest, NextResponse } from "next/server";

// Configure route to allow long-running streaming responses
export const maxDuration = 300; // 5 minutes
export const dynamic = 'force-dynamic'; // Disable caching for streaming

// 1. You can use any service adapter here for multi-agent support. We use
//    the empty adapter since we're only using one agent.
const serviceAdapter = new ExperimentalEmptyAdapter();

// Helper to wait for backend to be ready (handles cold start race condition)
// Backend can take 30-60 seconds to start on cold start (loading agent, etc.)
async function waitForBackend(url: string, maxRetries = 60, delayMs = 1000): Promise<boolean> {
  console.log("Waiting for backend to be ready...");
  for (let i = 0; i < maxRetries; i++) {
    try {
      const healthUrl = url.replace(/\/$/, '') + '/health';
      const response = await fetch(healthUrl, { method: 'GET' });
      if (response.ok) {
        console.log(`Backend ready after ${i + 1} attempts`);
        return true;
      }
    } catch {
      // Backend not ready yet, wait and retry
      if (i < maxRetries - 1) {
        if (i % 5 === 0) {
          console.log(`Backend not ready, attempt ${i + 1}/${maxRetries}...`);
        }
        await new Promise(resolve => setTimeout(resolve, delayMs));
      }
    }
  }
  return false;
}

// 2. Build a Next.js API route that handles the CopilotKit runtime requests.
export const POST = async (req: NextRequest) => {
  // Extract Firebase ID token from Authorization header
  const authHeader = req.headers.get("authorization");

  // Get backend URL from environment variable, fallback to localhost for dev
  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000/";

  // Wait for backend to be ready (handles cold start)
  const backendReady = await waitForBackend(backendUrl);
  if (!backendReady) {
    console.error("Backend not ready after retries");
    return NextResponse.json(
      { error: "Backend service unavailable, please try again" },
      { status: 503 }
    );
  }

  // Create runtime with agent configured to pass auth token
  // Pass the full Authorization header as-is to the backend
  const runtime = new CopilotRuntime({
    agents: {
      "my_agent": new HttpAgent({
        url: backendUrl,
        headers: authHeader ? {
          "x-firebase-token": authHeader  // Use custom header to avoid conflicts
        } : {},
      }),
    }
  });

  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};