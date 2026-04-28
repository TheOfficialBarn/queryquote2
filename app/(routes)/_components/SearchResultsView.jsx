"use client";

/**
 * Authors: Aiden Barnard & Atharva Patil
 * Assignment: 767 IR Project (Movie Dataset Search Engine)
 * 
 * Prologue:
 * Shared search results experience for QueryQuote route pages.
 * 
 * Last updated: 2026-04-27 - Matched Authority and Legacy controls to the
 * reusable compact filter toggle styling.
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


function decadeLabel(decade) {
  return `${String(decade).slice(0, 3)}0s`;
}


function normalizeFilterValues(values) {
  return values
    .map((value) => String(value).trim())
    .filter(Boolean);
}


export function useTranscriptFilterOptions() {
  const [decadeFilterOptions, setDecadeFilterOptions] = useState([]);
  const [genreFilterOptions, setGenreFilterOptions] = useState([]);

  useEffect(() => {
    const controller = new AbortController();

    async function fetchTranscriptFacets() {
      try {
        const response = await fetch("/api/transcripts?facets=true&index_version=v2", {
          signal: controller.signal,
          cache: "no-store",
        });
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data?.error || "Transcript facets failed");
        }

        const decades = Array.isArray(data.decades) ? data.decades : [];
        setDecadeFilterOptions(
          decades.map((decade) => ({
            id: `${decade}s`,
            label: decadeLabel(decade),
            value: String(decade),
          })),
        );

        const genres = Array.isArray(data.genres) ? data.genres : [];
        setGenreFilterOptions(
          genres.map((genre) => ({
            id: `genre-${genre}`,
            label: genre,
            value: genre,
          })),
        );
      } catch (error) {
        if (error.name === "AbortError") {
          return;
        }

        setDecadeFilterOptions([]);
        setGenreFilterOptions([]);
      }
    }

    fetchTranscriptFacets();

    return () => controller.abort();
  }, []);

  return { decadeFilterOptions, genreFilterOptions };
}


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
  decades = [],
  genres = [],
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

  normalizeFilterValues(decades).forEach((decade) => params.append("decade", decade));
  normalizeFilterValues(genres).forEach((genre) => params.append("genre", genre));

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


// Renders a compact controlled multi-select dropdown for metadata filters
// shared by the landing and results search bars.
export function SearchFilterDropdown({
  label,
  options,
  selectedValues,
  isOpen,
  onOpenChange,
  onToggle,
}) {
  const selectedCount = selectedValues.length;

  return (
    <details className="relative" open={isOpen}>
      <summary
        className="flex cursor-pointer list-none items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-sm text-white/85 transition-colors hover:bg-white/20 [&::-webkit-details-marker]:hidden"
        onClick={(event) => {
          event.preventDefault();
          onOpenChange(!isOpen);
        }}
      >
        <span>{label}</span>
        {selectedCount ? (
          <span className="rounded-full bg-blue-400/25 px-1.5 py-0.5 text-xs text-blue-100">
            {selectedCount}
          </span>
        ) : null}
      </summary>
      <div className="absolute left-0 top-full z-30 mt-2 max-h-64 w-56 overflow-y-auto rounded-xl border border-white/15 bg-neutral-950 p-2 shadow-xl shadow-black/40">
        {options.length ? (
          options.map((option) => {
            const active = selectedValues.includes(option.value);
            return (
              <button
                key={option.id}
                type="button"
                onClick={() => onToggle(option.value)}
                className={`flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                  active
                    ? "bg-blue-400/25 text-white"
                    : "text-white/80 hover:bg-white/10"
                }`}
                aria-pressed={active}
              >
                <span>{option.label}</span>
                <span className="text-xs text-blue-200">{active ? "Selected" : ""}</span>
              </button>
            );
          })
        ) : (
          <p className="px-3 py-2 text-sm text-white/55">No filters loaded</p>
        )}
      </div>
    </details>
  );
}


// Renders the sticky results-page search bar, including query input, search
// button, search mode controls, and query duration display.
function TopSearchBar({
  query,
  authorityFilter,
  legacySearch,
  activeDecades,
  activeGenres,
  decadeFilterOptions,
  genreFilterOptions,
  isSearching,
  queryDurationMs,
  onQueryChange,
  onAuthorityFilterChange,
  onLegacySearchChange,
  onDecadeToggle,
  onGenreToggle,
  onClearFilters,
  onSubmit,
}) {
  const hasActiveMetadataFilters = activeDecades.length > 0 || activeGenres.length > 0;
  const [openFilterDropdown, setOpenFilterDropdown] = useState(null);

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
                ? "border-blue-300/80 bg-blue-400/30 text-white"
                : "border-white/20 bg-white/10 text-white/85 hover:bg-white/20"
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
                ? "border-blue-300/80 bg-blue-400/30 text-white"
                : "border-white/20 bg-white/10 text-white/85 hover:bg-white/20"
            }`}
            aria-pressed={legacySearch}
          >
            Legacy Search
          </button>
          <SearchFilterDropdown
            label="Decades"
            options={decadeFilterOptions}
            selectedValues={activeDecades}
            isOpen={openFilterDropdown === "decades"}
            onOpenChange={(isOpen) => setOpenFilterDropdown(isOpen ? "decades" : null)}
            onToggle={onDecadeToggle}
          />
          <SearchFilterDropdown
            label="Genres"
            options={genreFilterOptions}
            selectedValues={activeGenres}
            isOpen={openFilterDropdown === "genres"}
            onOpenChange={(isOpen) => setOpenFilterDropdown(isOpen ? "genres" : null)}
            onToggle={onGenreToggle}
          />
          {hasActiveMetadataFilters ? (
            <button
              type="button"
              onClick={onClearFilters}
              className="rounded-full border border-white/20 bg-white/5 px-3 py-1 text-sm text-white/70 transition-colors hover:bg-white/15"
            >
              Clear filters
            </button>
          ) : null}
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
  const transcriptHref = `/transcripts/${encodeURIComponent(result.movie_id)}`;

  return (
    <Link href={transcriptHref} className="block">
      <article className="rounded-2xl border border-white/15 bg-black/35 p-4 transition-colors hover:border-blue-300/50 hover:bg-blue-500/10 sm:p-5">
        <p className="text-xs text-blue-300/80">Score: {scoreLabel}</p>
        {/* Regex in .replace() removes the underscores leftover from tokenization */}
        {/* However, it is an underscore before "S" it turns into an apostrophe */}
        <h2 className="mt-1 text-xl text-blue-300">{result.movie_id.replace(/_s\b/g, "'s").replace(/_/g,"")}</h2>
        <p className="mt-2 text-sm text-white/80">{result.snippet}</p>
        <p className="mt-3 break-all text-xs text-white/55">Source: {result.source_file}</p>
      </article>
    </Link>
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
  initialDecades = [],
  initialGenres = [],
  pathname = "/search",
}) {
  const router = useRouter();
  const { decadeFilterOptions, genreFilterOptions } = useTranscriptFilterOptions();
  const [query, setQuery] = useState(initialQuery);
  const [authorityFilter, setAuthorityFilter] = useState(initialAuthorityFilter);
  const [legacySearch, setLegacySearch] = useState(initialIndexVersion === "v1");
  const [activeDecades, setActiveDecades] = useState(initialDecades);
  const [activeGenres, setActiveGenres] = useState(initialGenres);
  const [responseData, setResponseData] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [queryDurationMs, setQueryDurationMs] = useState(null);
  const initialDecadeKey = initialDecades.join("|");
  const initialGenreKey = initialGenres.join("|");

  useEffect(() => {
    if (!initialQuery.trim()) {
      return;
    }

    const controller = new AbortController();


    // Fetches search results for the current URL query while updating loading,
    // error, result, and timer state.
    async function fetchResults() {
      const requestDecades = initialDecadeKey ? initialDecadeKey.split("|") : [];
      const requestGenres = initialGenreKey ? initialGenreKey.split("|") : [];
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
            decades: requestDecades,
            genres: requestGenres,
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
  }, [initialAuthorityFilter, initialDecadeKey, initialGenreKey, initialIndexVersion, initialQuery]);

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
    const metadataFilterCount = initialDecades.length + initialGenres.length;
    const metadataFilterLabel = metadataFilterCount > 0 ? ` with ${metadataFilterCount} metadata filter${metadataFilterCount === 1 ? "" : "s"}` : "";
    const pageLabel = resultCount > searchResultsPerPage ? `, page ${currentPage} of ${pageCount}` : "";
    return `${resultCount} result${resultCount === 1 ? "" : "s"}${indexLabel}${filterLabel}${metadataFilterLabel}${pageLabel}`;
  }, [currentPage, initialDecades.length, initialGenres.length, initialQuery, isSearching, pageCount, responseData?.authority_filter, responseData?.index_version, resultCount]);


  // Handles a new search from the sticky search bar by validating
  // input and routing to a fresh search results URL.
  function handleSubmit(event) {
    event.preventDefault();

    if (!query.trim() || isSearching) {
      return;
    }

    router.push(
      buildSearchResultsUrl({
        query,
        authorityFilter,
        legacySearch,
        decades: activeDecades,
        genres: activeGenres,
        pathname,
      }),
    );
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
        decades: initialDecades,
        genres: initialGenres,
        pathname,
      }),
    );
  }


  function toggleFilterValue(values, nextValue) {
    return values.includes(nextValue)
      ? values.filter((value) => value !== nextValue)
      : [...values, nextValue];
  }

  return (
    <main className="min-h-screen">
      <TopSearchBar
        query={query}
        authorityFilter={authorityFilter}
        legacySearch={legacySearch}
        activeDecades={activeDecades}
        activeGenres={activeGenres}
        decadeFilterOptions={decadeFilterOptions}
        genreFilterOptions={genreFilterOptions}
        isSearching={isSearching}
        queryDurationMs={queryDurationMs}
        onQueryChange={setQuery}
        onAuthorityFilterChange={setAuthorityFilter}
        onLegacySearchChange={setLegacySearch}
        onDecadeToggle={(value) => setActiveDecades((values) => toggleFilterValue(values, value))}
        onGenreToggle={(value) => setActiveGenres((values) => toggleFilterValue(values, value))}
        onClearFilters={() => {
          setActiveDecades([]);
          setActiveGenres([]);
        }}
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
