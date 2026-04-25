/**
 * Prologue:
 * Server-side proxy route for quote search requests from the Next.js frontend.
 * Last updated: 2026-04-25 - Added Flask API proxy to keep backend URL/server details out of client code and avoid browser CORS issues.
 */
import { NextResponse } from "next/server";

const DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:5000";

function getBackendBaseUrl() {
  return process.env.QUERYQUOTE_API_BASE_URL || DEFAULT_BACKEND_BASE_URL;
}

export async function POST(request) {
  try {
    const body = await request.json();
    const query = typeof body?.query === "string" ? body.query.trim() : "";
    const topK = Number.isInteger(body?.top_k) ? body.top_k : 10;

    if (!query) {
      return NextResponse.json(
        { error: "Query is required", results: [], count: 0 },
        { status: 400 },
      );
    }

    const response = await fetch(`${getBackendBaseUrl()}/api/search`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query, top_k: topK }),
      cache: "no-store",
    });

    const data = await response.json();

    return NextResponse.json(data, {
      status: response.status,
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: "Unable to reach search backend",
        details: error instanceof Error ? error.message : "Unknown error",
        results: [],
        count: 0,
      },
      { status: 502 },
    );
  }
}
