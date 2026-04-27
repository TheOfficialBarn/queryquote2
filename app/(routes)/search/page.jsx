"use client";

/**
 * Authors: Aiden Barnard & Atharva Patil
 * Assignment: 767 IR Project (Movie Dataset Search Engine)
 * 
 * Prologue:
 * Search route UI for quote discovery with a search-first experience and quick filters.
 * 
 * Last updated: 2026-04-27 - Added a Legacy Search toggle so users can
 * compare v1 against the default v2 search path from the frontend.
 */

import { Suspense, useState } from "react";
import { Jersey_10 } from "next/font/google";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import SearchResultsView, {
  buildSearchResultsUrl,
  normalizeSearchPage,
} from "../_components/SearchResultsView";

// Queryquote font
const movieFont = Jersey_10({
  weight: ["400"],
  subsets: ["latin"],
});

// Marquee quote ideas that scroll through search bar when no query typed in
const tickerQuotes = [
  '"I\'ll be back"',
  '"Why so serious?"',
  '"I drink your milkshake!"',
  '"Roads? Where we\'re going, we don\'t need roads."',
];

// Renders landing-page binary search option toggles before the first request.
function SearchOptionToggle({ enabled, onChange, label, description, enabledClassName }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!enabled)}
      className={`mt-4 rounded-2xl border px-4 py-3 text-left transition-colors ${
        enabled
          ? enabledClassName
          : "border-white/15 bg-white/5 text-white/85 hover:bg-white/10"
      }`}
      aria-pressed={enabled}
    >
      <span className="block text-sm font-semibold">{label}</span>
      <span className="mt-1 block text-xs text-white/70">
        {description}
      </span>
    </button>
  );
}

function SearchLandingPage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [useAuthorityFilter, setUseAuthorityFilter] = useState(false);
  const [useLegacySearch, setUseLegacySearch] = useState(false);

  async function handleSearch(event) {
    event.preventDefault();

    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      return;
    }

    router.push(
      buildSearchResultsUrl({
        query: trimmedQuery,
        authorityFilter: useAuthorityFilter,
        legacySearch: useLegacySearch,
      }),
    );
  }

  return (
    <main>
      {/* Hyperlinks */}
      <section className="absolute top-6 flex w-full justify-between px-6">
        <div className="flex gap-4">
          <Link href="/" className="hover:underline hover:text-blue-500">About</Link>
          <Link href="/how" className="hover:underline hover:text-blue-500">How it Works</Link>
        </div>
        <div className="flex gap-4">
          <Link href="https://www.regmovies.com/" className="hover:underline hover:text-blue-500">Movies Out Now</Link>
          <Link href="/transcripts" className="hover:underline hover:text-blue-500">Transcripts</Link>
        </div>
      </section>

      {/* Search */}
      <div className="min-h-screen px-6 py-16 md:py-20 flex items-center justify-center">
        <section className="mx-auto w-full max-w-3xl text-center">
          <p className="text-xs uppercase tracking-[0.25em]">
            <span className="bg-linear-to-r from-blue-700 via-purple-700 to-indigo-800 bg-clip-text text-transparent">
              Query Quote
            </span>
          </p>
          <h1 className={`${movieFont.className} mt-2 text-5xl md:text-6xl tracking-wide`}>
            Find The Right Movie
          </h1>
          <p className="mt-4 mx-auto max-w-2xl text-white/80">
            Search by exact quote or rough wording. We will help you track down the movie & scene you are thinking of.
          </p>

          <form className="mt-8" onSubmit={handleSearch}>
            <div className="flex items-center gap-2 bg-white rounded-full p-1 text-black transition-shadow duration-150 focus-within:ring-2 focus-within:ring-blue-500/80 focus-within:ring-offset-2 focus-within:ring-offset-transparent">
              {/* Search Icon from Heroicons.com */}
              <SearchIcon />
              {/* Search Bar */}
              <div className="relative w-full">
                <input
                  type="search"
                  placeholder="Search for a quote..."
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  className="peer w-full bg-transparent outline-none placeholder:text-transparent"
                  autoComplete="off"
                />

                {/* This is the animated placeholder marquee text that scrolls when the search bar input is empty */}
                <div className="pointer-events-none absolute inset-y-0 left-0 right-0 hidden items-center overflow-hidden peer-placeholder-shown:flex peer-focus:hidden">
                  <div className="quote-ticker-inline">
                    {[...tickerQuotes, ...tickerQuotes].map((quote, index) => (
                      <span
                        key={`${quote}-inline-${index}`}
                        className="mx-3 whitespace-nowrap text-black/55"
                      >
                        {quote}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
              {/* Search Button */}
              <button
                type="submit"
                disabled={!query.trim()}
                className="bg-black text-white rounded-full p-3 font-semibold tracking-tight transition-all duration-150 hover:bg-neutral-950 active:scale-95 focus-visible:ring-blue-500/60 disabled:cursor-not-allowed disabled:bg-neutral-700"
              >
                Search
              </button>
            </div>
            {/* Search option toggles */}
            <div className="flex flex-wrap justify-center gap-3">
              <SearchOptionToggle
                enabled={useAuthorityFilter}
                onChange={setUseAuthorityFilter}
                label="Authority filter"
                description="Boost movies with more Metacritic votes and lower sparse-review matches."
                enabledClassName="border-emerald-300/60 bg-emerald-300/15 text-white"
              />
              <SearchOptionToggle
                enabled={useLegacySearch}
                onChange={setUseLegacySearch}
                label="Legacy Search"
                description="Use the original v1 index instead of the default v2 search."
                enabledClassName="border-amber-300/70 bg-amber-300/20 text-white"
              />
            </div>
          </form>
        </section>
      </div>
    </main>
  );
}

// This function deicdes what the /search page should show based on the URL query parameters
// e.g. localhost:3000/search?{ Query }
function SearchPageContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";
  const initialPage = normalizeSearchPage(searchParams.get("page"));
  const initialAuthorityFilter = searchParams.get("authority_filter") === "true";
  const initialIndexVersion = searchParams.get("index_version") === "v1" ? "v1" : "v2";
  const pageStateKey = `${initialQuery}-${initialAuthorityFilter}-${initialIndexVersion}`;

  if (initialQuery.trim()) {
    return (
      // Will return the Search Results Page (meant to look like the page you see after searching something on Google)
      <SearchResultsView
        key={pageStateKey}
        initialQuery={initialQuery}
        initialPage={initialPage}
        initialAuthorityFilter={initialAuthorityFilter}
        initialIndexVersion={initialIndexVersion}
      />
    );
  }

  // Remain on localhost:3000/search if no query provided
  return <SearchLandingPage />;
}

// We have to wrap the page in Suspense because:
// SearchPageContent uses the Next hook: useSearchParams();
export default function SearchPage() {
  return (
    <Suspense fallback={<main className="min-h-screen p-6 text-white/70">Loading search...</main>}>
      <SearchPageContent />
    </Suspense>
  );
}

// Magnifying Glass copied from Heroicons.com
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
