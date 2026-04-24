/**
 * Prologue:
 * Search route UI for quote discovery with a search-first experience and quick filters.
 * Last updated: 2026-04-23 - Fixed frozen inline suggestions by switching to a dedicated ticker animation class.
 */
import { Jersey_10 } from "next/font/google";

const movieFont = Jersey_10({
  weight: ["400"],
  subsets: ["latin"],
});

const quickFilters = ["Movie Title", "Year", "Decade"];
const tickerQuotes = [
  "\"I'll be back\"",
  "\"Why so serious?\"",
  "\"I drink your milkshake!\"",
  "\"Roads? Where we're going, we don't need roads.\"",
];

function FilterChips() {
  return (
    <div className="mt-5 flex flex-wrap justify-center gap-2">
      {quickFilters.map((filter) => (
        <button
          key={filter}
          type="button"
          className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-sm text-white/90 hover:bg-white/20 transition-colors"
        >
          {filter}
        </button>
      ))}
    </div>
  );
}

export default function SearchPage() {
  return (
    <main className="min-h-screen px-6 flex items-center justify-center">
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
          Search by exact quote or rough wording. We will
          help you track down the movie line you are thinking of.
        </p>

        {/* Search */}
        <div className="mt-8">
          <div className="flex items-center gap-2 bg-white rounded-full p-1 text-black transition-shadow duration-150 focus-within:ring-2 focus-within:ring-blue-500/80 focus-within:ring-offset-2 focus-within:ring-offset-transparent">
            <SearchIcon/>
            <div className="relative w-full">
              <input
                type="search"
                placeholder="Search for a quote..."
                className="peer w-full bg-transparent outline-none placeholder:text-transparent"
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
              className="bg-black text-white rounded-full p-3 font-semibold tracking-tight transition-all duration-150 hover:bg-neutral-950 active:scale-95 focus-visible:ring-blue-500/60"
            >
              Search
            </button>
          </div>
          <FilterChips />
        </div>
      </section>
    </main>
  );
}

const SearchIcon = () => (
              <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="size-8 ml-2"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
              />
            </svg>
)
