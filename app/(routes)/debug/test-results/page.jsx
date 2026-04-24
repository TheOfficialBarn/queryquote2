/**
 * Prologue:
 * Debug-only simulated search results screen for visual testing and layout iteration.
 * Last updated: 2026-04-23 - Increased left padding and aligned search/filter edges with results cards.
 */
import { Jersey_10 } from "next/font/google";
import Link from "next/link";

const movieFont = Jersey_10({
  weight: ["400"],
  subsets: ["latin"],
});

const mockResults = [
  {
    title: "\"You had me at hello\" quote meaning and movie context",
    url: "queryquote.dev/movie/jerry-maguire/you-had-me-at-hello",
    snippet:
      "Identified as Jerry Maguire (1996). Spoken by Dorothy Boyd. Includes scene notes, timestamp references, and similar romantic lines.",
  },
  {
    title: "Top matches for: \"I drink your milkshake\"",
    url: "queryquote.dev/movie/there-will-be-blood/milkshake-scene",
    snippet:
      "Found in There Will Be Blood (2007). Character: Daniel Plainview. Compare with similar quotes by tone, decade, and actor.",
  },
  {
    title: "Quote search results for: \"Roads? Where we're going...\"",
    url: "queryquote.dev/movie/back-to-the-future/roads-quote",
    snippet:
      "Back to the Future (1985), spoken by Doc Brown. Includes franchise cross-references and alternate quote phrasings.",
  },
  {
    title: "Best fuzzy match for: \"Why so serious\"",
    url: "queryquote.dev/movie/the-dark-knight/why-so-serious",
    snippet:
      "The Dark Knight (2008). Speaker: The Joker. Includes clip context, tone tags, and associated quotes from the same scene.",
  },
];
const debugFilters = ["Movie Title", "Year", "Decade", "Exact Match"];

function SearchIcon() {
  return (
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
  );
}

function TopSearchBar() {
  return (
    <header className="sticky top-0 z-20 border-b border-white/15 bg-black/50 backdrop-blur-sm">
      <div className="grid w-full grid-cols-1 pl-4 pr-3 py-4 sm:pl-6 sm:pr-4 lg:grid-cols-[1fr_325px]">
        <div className="space-y-3">
          <Link href="/" className={`${movieFont.className} inline-block whitespace-nowrap text-3xl leading-none md:text-4xl`}>
            <span className="bg-linear-to-r from-blue-700 via-purple-700 to-indigo-800 bg-clip-text text-transparent">
              Query Quote
            </span>
          </Link>
          <div className="flex w-full items-center gap-2 bg-white rounded-full text-black transition-shadow duration-150 focus-within:ring-2 focus-within:ring-blue-500/80 focus-within:ring-offset-2 focus-within:ring-offset-transparent p-1">
            <SearchIcon />
            <input
              defaultValue="you had me at hello"
              placeholder="Search for a quote..."
              className="peer w-full bg-transparent outline-none placeholder:text-transparent"
              aria-label="Search query"
            />
            <button
              type="submit"
              className="bg-black text-white rounded-full p-2 font-semibold tracking-tight transition-all duration-150 hover:bg-neutral-950 active:scale-95 focus-visible:ring-blue-500/60"
            >
              Search
            </button>
          </div>
        </div>
      </div>
      <div className="grid w-full grid-cols-1 pl-4 pr-3 pb-3 sm:pl-6 sm:pr-4 lg:grid-cols-[1fr_300px]">
        <div className="flex flex-wrap items-center gap-2">
          <button className="rounded-full border border-blue-400/70 bg-blue-500/25 px-3 py-1 text-sm text-white">
            All
          </button>
          {debugFilters.map((filter) => (
            <button
              key={filter}
              className="rounded-full border border-white/20 bg-white/10 px-3 py-1 text-sm text-white/85 hover:bg-white/20 transition-colors"
            >
              {filter}
            </button>
          ))}
        </div>
      </div>
    </header>
  );
}

function ResultCard({ result }) {
  return (
    <article className="rounded-2xl border border-white/15 bg-black/35 p-4 sm:p-5">
      <p className="text-xs text-blue-300/80">{result.url}</p>
      <h2 className="mt-1 text-xl text-blue-300 hover:underline">{result.title}</h2>
      <p className="mt-2 text-sm text-white/80">{result.snippet}</p>
    </article>
  );
}

function KnowledgePanel() {
  return (
    <aside className="rounded-2xl border border-white/15 bg-black/40 p-5">
      <h3 className={`${movieFont.className} text-3xl`}>
        <span className="bg-linear-to-r from-blue-700 via-purple-700 to-indigo-800 bg-clip-text text-transparent">
          QueryQuote
        </span>
      </h3>
      <p className="mt-2 text-sm text-white/80">
        Debug preview of a results page with mock quote matches, metadata, and ranking layout.
      </p>
      <div className="mt-4 space-y-2 text-sm">
        <p className="text-white/90">Matches found: <span className="text-white">About 1,280</span></p>
        <p className="text-white/90">Avg confidence: <span className="text-white">92.4%</span></p>
        <p className="text-white/90">Primary mode: <span className="text-white">Fuzzy quote search</span></p>
      </div>
    </aside>
  );
}

export default function DebugTestResultsPage() {
  return (
    <main className="min-h-screen">
      <TopSearchBar />

      <section className="grid w-full grid-cols-1 gap-6 pl-4 pr-3 py-6 sm:pl-6 sm:pr-4 lg:grid-cols-[1fr_300px]">
        <div>
          <p className="mb-4 text-sm text-white/60">About 1,280 results (0.42 seconds)</p>
          <div className="space-y-4">
            {mockResults.map((result) => (
              <ResultCard key={result.url} result={result} />
            ))}
          </div>
        </div>
        <div className="lg:pt-8">
          <KnowledgePanel />
        </div>
      </section>
    </main>
  );
}
