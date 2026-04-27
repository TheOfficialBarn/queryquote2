"use client";

/**
 * Authors: Aiden Barnard & Atharva Patil
 * Assignment: 767 IR Project (Movie Dataset Search Engine)
 * 
 * Prologue:
 * Shared search results experience for QueryQuote route pages.
 * 
 * Last updated: 2026-04-27 - Added URL-backed Legacy Search selection so
 * frontend searches can target v1 while default searches use v2.
 */

import { useEffect, useMemo, useState } from "react";
import { Jersey_10 } from "next/font/google";
import Link from "next/link";
import { useRouter } from "next/navigation";

// QueryQuote's font
const movieFont = Jersey_10({
  weight: ["400"],
  subsets: ["latin"],
});

// Search results to search through
export const defaultSearchTopK = 50;
// How many appear "above-the-fold"
export const searchResultsPerPage = 25;


// Normalizes any page value from the URL into the supported search result pages.
export function normalizeSearchPage(value) {
  const parsed = Number(value);
  return parsed === 2 ? 2 : 1;
}


// Builds a shareable search results URL from the query, page, route path, and
// optional Authority Boost and Legacy Search settings.
export function buildSearchResultsUrl({
  query,
  page = 1,
  authorityFilter,
  legacySearch = false,
  pathname = "/search",
}) {
  const params = new URLSearchParams({
    q: query.trim(),
    page: String(normalizeSearchPage(page)),
    index_version: legacySearch ? "v1" : "v2",
  });

  if (authorityFilter) {
    params.set("authority_filter", "true");
  }

  return `${pathname}?${params.toString()}`;
}


// Rendrs the magnifying glass icon used by search inputs in the results view.
// Used from Heroicons.com
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


// Renders the sticky results-page search bar, including query input, search
// button, search mode controls, and query duration display.
function TopSearchBar({
  query,
  authorityFilter,
  legacySearch,
  isSearching,
  queryDurationMs,
  onQueryChange,
  onAuthorityFilterChange,
  onLegacySearchChange,
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
          <button
            type="button"
            onClick={() => onAuthorityFilterChange(!authorityFilter)}
            className={`rounded-full border px-3 py-1 text-sm transition-colors active:scale-95 ${
              authorityFilter
                ? "border-emerald-300/70 bg-emerald-400/60"
                : "border-white/20 bg-emerald-700/30 hover:bg-emerald-500/60 "
            }`}
            aria-pressed={authorityFilter}
          >
            Authority Boost
          </button>
          <button
            type="button"
            onClick={() => onLegacySearchChange(!legacySearch)}
            className={`rounded-full border px-3 py-1 text-sm transition-colors active:scale-95 ${
              legacySearch
                ? "border-amber-300/70 bg-amber-400/55 text-black"
                : "border-white/20 bg-white/10 text-white/85 hover:bg-white/20"
            }`}
            aria-pressed={legacySearch}
          >
            Legacy Search
          </button>
        </div>
      </div>
    </header>
  );
}


// Renders page navigation for the two client-side search result pages when
// enough results exist to paginate.
function PaginationControls({ currentPage, pageCount, onPageChange }) {
  if (pageCount < 2) {
    return null;
  }

  return (
    <nav className="mb-4 flex flex-wrap items-center gap-2" aria-label="Search results pages">
      {[1, 2].map((page) => (
        <button
          key={page}
          type="button"
          onClick={() => onPageChange(page)}
          className={`rounded-full border px-3 py-1 text-sm transition-colors active:scale-95 ${
            currentPage === page
              ? "border-blue-400/70 bg-blue-500/25 text-white"
              : "border-white/20 bg-white/10 text-white/85 hover:bg-white/20"
          }`}
          aria-current={currentPage === page ? "page" : undefined}
        >
          Page {page}
        </button>
      ))}
    </nav>
  );
}


// Renders one search result card with score, movie identifier, snippet, and
// source file metadata.
function ResultCard({ result }) {
  const score = Number(result.score);
  const scoreLabel = Number.isFinite(score) ? score.toFixed(3) : "n/a";

  return (
    <article className="rounded-2xl border border-white/15 bg-black/35 p-4 sm:p-5">
      <p className="text-xs text-blue-300/80">Score: {scoreLabel}</p>
      {/* Regex in .replace() removes the underscores leftover from tokenization */}
      {/* However, it is an underscore before "S" it turns into an apostrophe */}
      <h2 className="mt-1 text-xl text-blue-300">{result.movie_id.replace(/_s\b/g, "'s").replace(/_/g,"")}</h2>
      <p className="mt-2 text-sm text-white/80">{result.snippet}</p>
      <p className="mt-3 break-all text-xs text-white/55">Source: {result.source_file}</p>
    </article>
  );
}


// Renders the empty state shown when the backend returns no matching quote
// results or when the search request fails.
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


// Converts an elapsed query duration in milliseconds into padded
// hours/minutes/seconds/milliseconds segments for display.
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


// Displays the formatted query timer with separate visual styling for each
// time segment.
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


// Renders the right-side search metadata panel that summarizes the current
// query, result count, requested count, page, index version, and boost state.



// Coordinates the search results experience by fetching results, tracking
// search state, routing new searches, paginating results, and rendering the
// results layout.
export default function SearchResultsView({
  initialQuery,
  initialPage = 1,
  initialAuthorityFilter,
  initialIndexVersion = "v2",
  pathname = "/search",
}) {
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);
  const [authorityFilter, setAuthorityFilter] = useState(initialAuthorityFilter);
  const [legacySearch, setLegacySearch] = useState(initialIndexVersion === "v1");
  const [responseData, setResponseData] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [queryDurationMs, setQueryDurationMs] = useState(null);

  useEffect(() => {
    if (!initialQuery.trim()) {
      return;
    }

    const controller = new AbortController();


    // Fetches search results for the current URL query while updating loading,
    // error, result, and timer state.
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
            top_k: defaultSearchTopK,
            authority_filter: initialAuthorityFilter,
            index_version: initialIndexVersion,
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
  }, [initialAuthorityFilter, initialIndexVersion, initialQuery]);

  const results = responseData?.results ?? [];
  const resultCount = typeof responseData?.count === "number" ? responseData.count : 0;
  const pageCount = resultCount > searchResultsPerPage ? 2 : 1;
  const currentPage = Math.min(normalizeSearchPage(initialPage), pageCount);
  const visibleResults = results.slice(
    (currentPage - 1) * searchResultsPerPage,
    currentPage * searchResultsPerPage,
  );
  const resultSummary = useMemo(() => {
    if (!initialQuery.trim()) {
      return "Enter a quote to search.";
    }

    if (isSearching) {
      return `Searching for "${initialQuery}"...`;
    }

    const indexLabel = responseData?.index_version === "v1" ? " with legacy search" : "";
    const filterLabel = responseData?.authority_filter ? " with authority filter" : "";
    const pageLabel = resultCount > searchResultsPerPage ? `, page ${currentPage} of ${pageCount}` : "";
    return `${resultCount} result${resultCount === 1 ? "" : "s"}${indexLabel}${filterLabel}${pageLabel}`;
  }, [currentPage, initialQuery, isSearching, pageCount, responseData?.authority_filter, responseData?.index_version, resultCount]);


  // Handles a new search from the sticky search bar by validating
  // input and routing to a fresh search results URL.
  function handleSubmit(event) {
    event.preventDefault();

    if (!query.trim() || isSearching) {
      return;
    }

    router.push(buildSearchResultsUrl({ query, authorityFilter, legacySearch, pathname }));
  }


  // Handles results page changes by preserving the active query and Authority Boost
  // Setting while updating the page number in the URL
  function handlePageChange(page) {
    router.push(
      buildSearchResultsUrl({
        query: initialQuery,
        page,
        authorityFilter: initialAuthorityFilter,
        legacySearch: initialIndexVersion === "v1",
        pathname,
      }),
    );
  }

  return (
    <main className="min-h-screen">
      <TopSearchBar
        query={query}
        authorityFilter={authorityFilter}
        legacySearch={legacySearch}
        isSearching={isSearching}
        queryDurationMs={queryDurationMs}
        onQueryChange={setQuery}
        onAuthorityFilterChange={setAuthorityFilter}
        onLegacySearchChange={setLegacySearch}
        onSubmit={handleSubmit}
      />

      <section className="mx-auto grid w-full max-w-7xl grid-cols-1 gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[1fr_300px]">
        <div>
          <p className="mb-4 text-sm text-white/60">{resultSummary}</p>
          <PaginationControls
            currentPage={currentPage}
            pageCount={pageCount}
            onPageChange={handlePageChange}
          />
          <div className="space-y-4">
            {visibleResults.length ? (
              visibleResults.map((result) => (
                <ResultCard key={result.passage_id} result={result} />
              ))
            ) : !isSearching && initialQuery.trim() ? (
              <ResultsEmptyState query={initialQuery} errorMessage={errorMessage} />
            ) : null}
          </div>
        </div>
      </section>
    </main>
  );
}
