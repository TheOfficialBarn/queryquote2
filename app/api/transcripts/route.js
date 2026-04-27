/**
 * Authors: Aiden Barnard & Atharva Patil
 * Assignment: 767 IR Project (Movie Dataset Search Engine)
 *
 * Prologue:
 * Server-side proxy route for transcript browser requests from the Next.js UI.
 * (Fetches transcripts & movies from Flask Python backend)
 *
 * Last updated: 2026-04-27 - Passed repeated decade and genre filters through
 * to Flask for multi-select transcript browsing.
 */

import { NextResponse } from "next/server";

// Backend URL (Python Flask)
const DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:5000";

// Default browser list size; Flask still enforces its own maximum.
const DEFAULT_TRANSCRIPT_LIMIT = 40;

export async function GET(request) {
  try {
    const requestUrl = new URL(request.url);
    const backendUrl = new URL(`${DEFAULT_BACKEND_BASE_URL}/api/transcripts`);
    const query = requestUrl.searchParams.get("q")?.trim() || "";
    const movieId = requestUrl.searchParams.get("movie_id")?.trim() || "";
    const facets = requestUrl.searchParams.get("facets") === "true";
    const decades = requestUrl.searchParams
      .getAll("decade")
      .map((value) => value.trim())
      .filter(Boolean);
    const genres = requestUrl.searchParams
      .getAll("genre")
      .map((value) => value.trim())
      .filter(Boolean);
    const indexVersion = requestUrl.searchParams.get("index_version") === "v1" ? "v1" : "v2";
    const parsedLimit = Number(requestUrl.searchParams.get("limit"));
    const limit = Number.isInteger(parsedLimit) ? parsedLimit : DEFAULT_TRANSCRIPT_LIMIT;

    if (movieId) {
      backendUrl.searchParams.set("movie_id", movieId);
    } else if (facets) {
      backendUrl.searchParams.set("facets", "true");
    } else if (query) {
      backendUrl.searchParams.set("q", query);
    }

    decades.forEach((decade) => backendUrl.searchParams.append("decade", decade));
    genres.forEach((genre) => backendUrl.searchParams.append("genre", genre));

    backendUrl.searchParams.set("limit", String(limit));
    backendUrl.searchParams.set("index_version", indexVersion);

    const response = await fetch(backendUrl, {
      method: "GET",
      cache: "no-store",
    });
    const data = await response.json();

    return NextResponse.json(data, {
      status: response.status,
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: "Unable to reach transcript backend",
        details: error instanceof Error ? error.message : "Unknown error",
        results: [],
        count: 0,
      },
      { status: 502 },
    );
  }
}
