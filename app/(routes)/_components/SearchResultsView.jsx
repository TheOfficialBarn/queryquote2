"use client";

/**
 * Prologue:
 * Shared search results experience for QueryQuote route pages.
 * Last updated: 2026-04-26 - Set the shared default result count to Top 25
 * while keeping the selectable search count options in one place.
 */
import { useEffect, useMemo, useState } from "react";
import { Jersey_10 } from "next/font/google";
import Link from "next/link";
import { useRouter } from "next/navigation";

const movieFont = Jersey_10({
  weight: ["400"],
  subsets: ["latin"],
});

export const defaultSearchTopK = 25;
export const searchTopKOptions = [5, 10, 20, defaultSearchTopK];

export function normalizeSearchTopK(value) {
  const parsed = Number(value);
  return searchTopKOptions.includes(parsed) ? parsed : defaultSearchTopK;
}

export function buildSearchResultsUrl({
  query,
  topK,
  authorityFilter,
  pathname = "/search",
}) {
  const params = new URLSearchParams({
    q: query.trim(),
    top_k: String(topK),
  });

  if (authorityFilter) {
    params.set("authority_filter", "true");
  }

  return `${pathname}?${params.toString()}`;
}

function SearchIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      className="size-8 ml-2"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
      />
    </svg>
  );
}

function TopSearchBar({
  query,
  topK,
  authorityFilter,
  isSearching,
  queryDurationMs,
  onQueryChange,
  onTopKChange,
  onAuthorityFilterChange,
  onSubmit,
}) {
  return (
    <header className="sticky top-0 z-20 border-b border-white/15 bg-black/50 backdrop-blur-sm">
      <div className="mx-auto grid w-full max-w-7xl grid-cols-1 gap-4 px-4 py-4 sm:px-6 lg:grid-cols-[1fr_325px] lg:items-end">
        <div className="space-y-3">
          <Link href="/search" className={`${movieFont.className} inline-block whitespace-nowrap text-3xl leading-none md:text-4xl`}>
            <span className="bg-linear-to-r from-blue-700 via-purple-700 to-indigo-800 bg-clip-text text-transparent">
              Query Quote
            </span>
          </Link>
          <form
            className="flex w-full items-center gap-2 bg-white rounded-full text-black transition-shadow duration-150 focus-within:ring-2 focus-within:ring-blue-500/80 focus-within:ring-offset-2 focus-within:ring-offset-transparent p-1"
            onSubmit={onSubmit}
          >
            <SearchIcon />
            <input
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder="Search for a quote..."
              className="w-full bg-transparent outline-none placeholder:text-black/45"
              aria-label="Search query"
            />
            <button
              type="submit"
              disabled={isSearching || !query.trim()}
              className="bg-black text-white rounded-full p-2 font-semibold tracking-tight transition-all duration-150 hover:bg-neutral-950 active:scale-95 focus-visible:ring-blue-500/60 disabled:cursor-not-allowed disabled:bg-neutral-700"
            >
              {isSearching ? "Searching..." : "Search"}
            </button>
          </form>
        </div>
        <div
          className={`${movieFont.className} text-5xl text-white lg:justify-self-center`}
          aria-live={isSearching ? "polite" : "off"}
        >
          <QueryDurationText durationMs={queryDurationMs} />
        </div>
      </div>
      <div className="mx-auto grid w-full max-w-7xl grid-cols-1 px-4 pb-3 sm:px-6 lg:grid-cols-[1fr_300px]">
        <div className="flex flex-wrap items-center gap-2">
          {searchTopKOptions.map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => onTopKChange(option)}
              className={`rounded-full border px-3 py-1 text-sm transition-colors active:scale-95 ${
                topK === option
                  ? "border-blue-400/70 bg-blue-500/25"
                  : "border-white/20 bg-white/10 text-white/85 hover:bg-white/20"
              }`}
              aria-pressed={topK === option}
            >
              Top {option}
            </button>
          ))}
          <button
            type="button"
            onClick={() => onAuthorityFilterChange(!authorityFilter)}
            className={`rounded-full border px-3 py-1 text-sm transition-colors active:scale-95 ${
              authorityFilter
                ? "border-emerald-300/70 bg-emerald-400/60"
                : "border-white/20 bg-emerald-600/60 hover:bg-emerald-500/60 "
            }`}
            aria-pressed={authorityFilter}
          >
            Authority Boost
          </button>
        </div>
      </div>
    </header>
  );
}

function ResultCard({ result }) {
  const score = Number(result.score);
  const scoreLabel = Number.isFinite(score) ? score.toFixed(3) : "n/a";

  return (
    <article className="rounded-2xl border border-white/15 bg-black/35 p-4 sm:p-5">
      <p className="text-xs text-blue-300/80">Score: {scoreLabel}</p>
      <h2 className="mt-1 text-xl text-blue-300">{result.movie_id}</h2>
      <p className="mt-2 text-sm text-white/80">{result.snippet}</p>
      <p className="mt-3 break-all text-xs text-white/55">Source: {result.source_file}</p>
    </article>
  );
}

function ResultsEmptyState({ query, errorMessage }) {
  return (
    <article className="rounded-2xl border border-white/15 bg-black/35 p-5">
      <h2 className="text-xl text-white">No matching quotes found</h2>
      <p className="mt-2 text-sm text-white/70">
        {errorMessage || `No backend matches came back for "${query}".`}
      </p>
    </article>
  );
}

function formatQueryDuration(durationMs) {
  const totalMs = Math.max(0, Math.floor(durationMs));
  const milliseconds = totalMs % 1000;
  const totalSeconds = Math.floor(totalMs / 1000);
  const seconds = totalSeconds % 60;
  const totalMinutes = Math.floor(totalSeconds / 60);
  const minutes = totalMinutes % 60;
  const hours = Math.floor(totalMinutes / 60);
  const pad = (value, size = 2) => String(value).padStart(size, "0");

  return {
    hours: pad(hours),
    minutes: pad(minutes),
    seconds: pad(seconds),
    milliseconds: pad(milliseconds, 3),
  };
}

function QueryDurationText({ durationMs }) {
  const duration = formatQueryDuration(durationMs ?? 0);
  const separatorClassName = "text-white/45";

  return (
    <>
      <span className="text-sky-200">{duration.hours}</span>
      <span className={separatorClassName}>:</span>
      <span className="text-violet-200">{duration.minutes}</span>
      <span className={separatorClassName}>:</span>
      <span className="text-fuchsia-200">{duration.seconds}</span>
      <span className={separatorClassName}>:</span>
      <span className="text-indigo-200">{duration.milliseconds}</span>
    </>
  );
}

function KnowledgePanel({ query, count, topK, authorityFilter }) {
  return (
    <aside className="rounded-2xl border border-white/15 bg-black/40 p-5">
      <h3 className={`${movieFont.className} text-3xl`}>
        <span className="bg-linear-to-r from-blue-700 via-purple-700 to-indigo-800 bg-clip-text text-transparent">
          QueryQuote
        </span>
      </h3>
      <p className="mt-2 text-sm text-white/80">
        Search settings and result metadata for the current quote lookup.
      </p>
      <div className="mt-4 space-y-2 text-sm">
        <p className="text-white/90">Query: <span className="text-white">{query || "None"}</span></p>
        <p className="text-white/90">Matches found: <span className="text-white">{count}</span></p>
        <p className="text-white/90">Requested count: <span className="text-white">Top {topK}</span></p>
        <p className="text-white/90">
          Authority filter: <span className="text-white">{authorityFilter ? "On" : "Off"}</span>
        </p>
      </div>
    </aside>
  );
}

export default function SearchResultsView({
  initialQuery,
  initialTopK,
  initialAuthorityFilter,
  pathname = "/search",
}) {
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);
  const [topK, setTopK] = useState(initialTopK);
  const [authorityFilter, setAuthorityFilter] = useState(initialAuthorityFilter);
  const [responseData, setResponseData] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [queryDurationMs, setQueryDurationMs] = useState(null);

  useEffect(() => {
    if (!initialQuery.trim()) {
      return;
    }

    const controller = new AbortController();

    async function fetchResults() {
      const startedAt = performance.now();
      const timerId = window.setInterval(() => {
        setQueryDurationMs(performance.now() - startedAt);
      }, 33);

      setIsSearching(true);
      setErrorMessage("");
      setQueryDurationMs(0);

      try {
        const response = await fetch("/api/search", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            query: initialQuery.trim(),
            top_k: initialTopK,
            authority_filter: initialAuthorityFilter,
          }),
          signal: controller.signal,
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data?.error || "Search request failed");
        }

        setResponseData(data);
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }

        setResponseData({ results: [], count: 0 });
        setErrorMessage(error instanceof Error ? error.message : "Unexpected search error");
      } finally {
        window.clearInterval(timerId);

        if (!controller.signal.aborted) {
          setQueryDurationMs(performance.now() - startedAt);
          setIsSearching(false);
        }
      }
    }

    fetchResults();

    return () => controller.abort();
  }, [initialAuthorityFilter, initialQuery, initialTopK]);

  const results = responseData?.results ?? [];
  const resultCount = typeof responseData?.count === "number" ? responseData.count : 0;
  const resultSummary = useMemo(() => {
    if (!initialQuery.trim()) {
      return "Enter a quote to search.";
    }

    if (isSearching) {
      return `Searching for "${initialQuery}"...`;
    }

    const filterLabel = responseData?.authority_filter ? " with authority filter" : "";
    return `${resultCount} result${resultCount === 1 ? "" : "s"}${filterLabel}`;
  }, [initialQuery, isSearching, responseData?.authority_filter, resultCount]);

  function handleSubmit(event) {
    event.preventDefault();

    if (!query.trim() || isSearching) {
      return;
    }

    router.push(buildSearchResultsUrl({ query, topK, authorityFilter, pathname }));
  }

  return (
    <main className="min-h-screen">
      <TopSearchBar
        query={query}
        topK={topK}
        authorityFilter={authorityFilter}
        isSearching={isSearching}
        queryDurationMs={queryDurationMs}
        onQueryChange={setQuery}
        onTopKChange={setTopK}
        onAuthorityFilterChange={setAuthorityFilter}
        onSubmit={handleSubmit}
      />

      <section className="mx-auto grid w-full max-w-7xl grid-cols-1 gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[1fr_300px]">
        <div>
          <p className="mb-4 text-sm text-white/60">{resultSummary}</p>
          <div className="space-y-4">
            {results.length ? (
              results.map((result) => (
                <ResultCard key={result.passage_id} result={result} />
              ))
            ) : !isSearching && initialQuery.trim() ? (
              <ResultsEmptyState query={initialQuery} errorMessage={errorMessage} />
            ) : null}
          </div>
        </div>
        <div className="lg:pt-8">
          <KnowledgePanel
            query={initialQuery}
            count={resultCount}
            topK={initialTopK}
            authorityFilter={initialAuthorityFilter}
          />
        </div>
      </section>
    </main>
  );
}
