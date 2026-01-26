import { NextResponse } from "next/server";

// Health check proxy to backend
// Avoids CORS issues and keeps backend URL server-side
export async function GET() {
  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000/";
  const healthUrl = backendUrl.replace(/\/$/, "") + "/health";

  try {
    const response = await fetch(healthUrl, {
      method: "GET",
      // Short timeout since we're polling frequently
      signal: AbortSignal.timeout(5000),
    });

    if (response.ok) {
      return NextResponse.json({ status: "ready" });
    }

    return NextResponse.json(
      { status: "unavailable" },
      { status: 503 }
    );
  } catch {
    return NextResponse.json(
      { status: "unavailable" },
      { status: 503 }
    );
  }
}
