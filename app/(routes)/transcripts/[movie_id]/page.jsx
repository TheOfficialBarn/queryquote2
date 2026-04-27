"use client";

/**
 * Authors: Aiden Barnard & Atharva Patil
 * Assignment: 767 IR Project (Movie Dataset Search Engine)
 *
 * Prologue:
 * This page is a Next.js [dynamic] route/page that opens one indexed movie
 * movie transcript from the URL movie_id segment
 *
 * Last updated: 2026-04-27 - Guarded the initial empty detail state so the
 * reader waits for transcript data before rendering source metadata.
 */

import { useEffect, useMemo, useState } from "react";
import { Jersey_10 } from "next/font/google";
import { useParams } from "next/navigation";
import RouteBackLink from "../../_components/RouteBackLink";

const movieFont = Jersey_10({
  weight: ["400"],
  subsets: ["latin"],
});

function decodeMovieId(value) {
  if (typeof value !== "string") {
    return "";
  }

  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function formatMovieLabel(movie) {
  if (!movie) {
    return "Transcript";
  }

  return movie.year ? `${movie.title} (${movie.year})` : movie.title;
}

function hasTranscriptDetail(data) {
  return Boolean(
    data
      && typeof data === "object"
      && data.movie
      && typeof data.source_file === "string"
      && typeof data.transcript === "string",
  );
}

export default function TranscriptDetailPage() {
  const params = useParams();
  const movieId = useMemo(() => decodeMovieId(params?.movie_id), [params]);
  const [detail, setDetail] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (!movieId) {
      return;
    }

    const controller = new AbortController();

    async function fetchTranscript() {
      setIsLoading(true);
      setErrorMessage("");

      const requestParams = new URLSearchParams({
        movie_id: movieId,
        index_version: "v2",
      });

      try {
        const response = await fetch(`/api/transcripts?${requestParams.toString()}`, {
          signal: controller.signal,
          cache: "no-store",
        });
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data?.error || "Unable to open transcript");
        }

        if (!hasTranscriptDetail(data)) {
          throw new Error("Transcript response was incomplete");
        }

        setDetail(data);
      } catch (error) {
        if (error.name === "AbortError") {
          return;
        }

        setDetail(null);
        setErrorMessage(error instanceof Error ? error.message : "Unable to open transcript");
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    fetchTranscript();

    return () => controller.abort();
  }, [movieId]);

  const genres = Array.isArray(detail?.movie?.genres) ? detail.movie.genres : [];
  const visibleErrorMessage = movieId ? errorMessage : "Missing movie id.";
  const shouldShowLoading = isLoading || (movieId && !detail && !visibleErrorMessage);

  return (
    <main className="min-h-screen px-6 py-8 md:px-8 md:py-10">
      <div className="mx-auto max-w-5xl">
        <RouteBackLink href="/transcripts" label="← Back to transcripts" />

        <section className="mt-8">
          <p className="text-xs uppercase tracking-[0.28em] text-white/55">
            Transcript
          </p>
          <h1 className={`${movieFont.className} mt-3 text-5xl tracking-wide text-white md:text-6xl`}>
            {formatMovieLabel(detail?.movie)}
          </h1>
          {genres.length ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {genres.map((genre) => (
                <span
                  key={genre}
                  className="rounded-full border border-white/15 bg-white/10 px-2 py-0.5 text-xs text-white/75"
                >
                  {genre}
                </span>
              ))}
            </div>
          ) : null}
        </section>

        <section className="mt-8 border border-white/15 bg-black/35">
          {shouldShowLoading ? (
            <p className="p-6 text-sm text-white/65">Loading transcript...</p>
          ) : visibleErrorMessage ? (
            <p className="p-6 text-sm text-red-100">{visibleErrorMessage}</p>
          ) : detail ? (
            <>
              <div className="border-b border-white/10 px-5 py-4">
                <p className="break-all text-xs text-white/45">
                  {detail.source_file}
                </p>
              </div>
              <pre className="max-h-[72vh] overflow-y-auto whitespace-pre-wrap px-5 py-5 font-mono text-sm leading-7 text-white/82">
                {detail.transcript}
              </pre>
            </>
          ) : (
            <p className="p-6 text-sm text-red-100">Transcript could not be loaded.</p>
          )}
        </section>
      </div>
    </main>
  );
}
