/**
 * Authors: Aiden Barnard & Atharva Patil
 * Assignment: 767 IR Project (Movie Dataset Search Engine)
 * 
 * Prologue:
 * Server-side proxy route for quote search requests from the Next.js frontend.
 * 
 * Last updated: 2026-04-27 - Defaults frontend searches to v2 while still
 * passing Legacy Search v1 requests and Authority Boost through to Flask.
 */

import { NextResponse } from "next/server";

// Backend URL (Python Flask)
const DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:5000";

// Amount of Search Results we want fetched
const DEFAULT_TOP_K = 50;

export async function POST(request) {
  try {
    const body = await request.json(); // Query body
    const query = typeof body?.query === "string" ? body.query.trim() : ""; // Trim body query
    const topK = Number.isInteger(body?.top_k) ? body.top_k : DEFAULT_TOP_K; // If topK is in body use it, if not then use DEFAULT_TOP_K
    const authorityFilter = body?.authority_filter === true; // AUTHORITY BOOST (MAY GET RID OF AT SOME POINT)
    const indexVersion = body?.index_version === "v1" ? "v1" : "v2";

    // Front-end HAS to provide a query in order to search backend
    if (!query) {
      return NextResponse.json(
        { error: "Query is required", results: [], count: 0 },
        { status: 400 },
      );
    }

    // Fetch respones from backend (flask python)
    const response = await fetch(`${DEFAULT_BACKEND_BASE_URL}/api/search`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query,
        top_k: topK,
        authority_filter: authorityFilter,
        index_version: indexVersion,
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
