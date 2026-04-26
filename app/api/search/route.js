/**
 * Prologue:
 * Server-side proxy route for quote search requests from the Next.js frontend.
 * Last updated: 2026-04-25 - Added opt-in authority filter passthrough so the
 * backend can weight rankings by Metacritic vote counts only when requested.
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
    const authorityFilter = body?.authority_filter === true;

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
      body: JSON.stringify({
        query,
        top_k: topK,
        authority_filter: authorityFilter,
      }),
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
