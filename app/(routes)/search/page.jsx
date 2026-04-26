"use client";

/**
 * Prologue:
 * Search route UI for quote discovery with a search-first experience and quick filters.
 * Last updated: 2026-04-26 - Uses /search?q=... as the normal results URL
 * while keeping the blank /search route as the initial search form.
 */
import { Suspense, useState } from "react";
import { Jersey_10 } from "next/font/google";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import SearchResultsView, {
  buildSearchResultsUrl,
  normalizeSearchTopK,
} from "../_components/SearchResultsView";

const movieFont = Jersey_10({
  weight: ["400"],
  subsets: ["latin"],
});

const topKOptions = [5, 10, 20];
const tickerQuotes = [
  '"I\'ll be back"',
  '"Why so serious?"',
  '"I drink your milkshake!"',
  '"Roads? Where we\'re going, we don\'t need roads."',
];

function TopKChips({ selectedTopK, onChange }) {
  return (
    <div className="mt-5 flex flex-wrap justify-center gap-2">
      {topKOptions.map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onChange(option)}
          className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${
            selectedTopK === option
              ? "border-white/60 bg-white/25 text-white"
              : "border-white/20 bg-white/10 text-white/90 hover:bg-white/20"
          }`}
          aria-pressed={selectedTopK === option}
        >
          Top {option}
        </button>
      ))}
    </div>
  );
}

function AuthorityFilterToggle({ enabled, onChange }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!enabled)}
      className={`mt-4 rounded-2xl border px-4 py-3 text-left transition-colors ${
        enabled
          ? "border-emerald-300/60 bg-emerald-300/15 text-white"
          : "border-white/15 bg-white/5 text-white/85 hover:bg-white/10"
      }`}
      aria-pressed={enabled}
    >
      <span className="block text-sm font-semibold">Authority filter</span>
      <span className="mt-1 block text-xs text-white/70">
        Boost movies with more Metacritic votes and lower sparse-review matches.
      </span>
    </button>
  );
}

function SearchLandingPage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(10);
  const [useAuthorityFilter, setUseAuthorityFilter] = useState(false);

  async function handleSearch(event) {
    event.preventDefault();

    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      return;
    }

    router.push(
      buildSearchResultsUrl({
        query: trimmedQuery,
        topK,
        authorityFilter: useAuthorityFilter,
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
            <SearchIcon />
            <div className="relative w-full">
              <input
                type="search"
                placeholder="Search for a quote..."
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="peer w-full bg-transparent outline-none placeholder:text-transparent"
                autoComplete="off"
              />
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
            <button
              type="submit"
              disabled={!query.trim()}
              className="bg-black text-white rounded-full p-3 font-semibold tracking-tight transition-all duration-150 hover:bg-neutral-950 active:scale-95 focus-visible:ring-blue-500/60 disabled:cursor-not-allowed disabled:bg-neutral-700"
            >
              Search
            </button>
          </div>
          <TopKChips selectedTopK={topK} onChange={setTopK} />
          <div className="flex justify-center">
            <AuthorityFilterToggle
              enabled={useAuthorityFilter}
              onChange={setUseAuthorityFilter}
            />
          </div>
        </form>

      </section>
      </div>
    </main>
  );
}

function SearchPageContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";
  const initialTopK = normalizeSearchTopK(searchParams.get("top_k"));
  const initialAuthorityFilter = searchParams.get("authority_filter") === "true";
  const pageStateKey = `${initialQuery}-${initialTopK}-${initialAuthorityFilter}`;

  if (initialQuery.trim()) {
    return (
      <SearchResultsView
        key={pageStateKey}
        initialQuery={initialQuery}
        initialTopK={initialTopK}
        initialAuthorityFilter={initialAuthorityFilter}
      />
    );
  }

  return <SearchLandingPage />;
}

export default function SearchPage() {
  return (
    <Suspense fallback={<main className="min-h-screen p-6 text-white/70">Loading search...</main>}>
      <SearchPageContent />
    </Suspense>
  );
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
