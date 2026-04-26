/**
 * Prologue:
 * Simplified implementation for the QueryQuote "How it Works" page.
 * The page is now driven by a few compact data structures and one shared section
 * renderer so the route stays easy to scan and update without repeated card markup.
 * Last updated: 2026-04-25 - Added route-level scroll snapping so the intro and
 * each major content panel settle into place during vertical scrolling.
 */
import { Jersey_10 } from "next/font/google";
import RouteBackLink from "../_components/RouteBackLink";

const movieFont = Jersey_10({
  weight: ["400"],
  subsets: ["latin"],
});

const overviewItems = [
  ["Frontend", "Next.js 16 App Router, React 19, Tailwind CSS 4"],
  ["Backend API", "Python 3.10+ with Flask"],
  ["Search Storage", "SQLite index for large corpora, pickle bundle as a legacy option"],
  ["Ranking", "BM25, TF-IDF cosine similarity, and quote-aware reranking"],
];

const sections = [
  {
    title: "Tech Stack",
    columns: "md:grid-cols-2",
    items: [
      {
        title: "Frontend",
        body:
          "The web app runs on Next.js 16 with the App Router and React 19. Styling is handled with Tailwind CSS 4, and the current UI uses custom typography plus a shared global background defined in the root layout.",
      },
      {
        title: "Backend",
        body:
          "The search API is a Flask service packaged as a Python project. It exposes health and search endpoints and can load either the SQLite-backed index or the legacy pickle bundle, depending on how the index was built.",
      },
    ],
  },
  {
    title: "Implementation Pipeline",
    columns: "md:grid-cols-2 xl:grid-cols-3",
    items: [
      {
        title: "1. Transcript ingestion",
        body:
          "Raw movie transcript files are collected and split into overlapping passages so the engine can rank smaller quote-sized chunks instead of entire files.",
      },
      {
        title: "2. Text normalization",
        body:
          "Both transcripts and user queries are tokenized and normalized to improve matching when punctuation is missing, remembered loosely, or written slightly differently.",
      },
      {
        title: "3. Index building",
        body:
          "QueryQuote builds an inverted positional index. Each term points to the passages where it appears, along with term frequency and token positions for phrase and proximity checks.",
      },
      {
        title: "4. Lexical retrieval",
        body:
          "At query time, the engine gathers candidate passages, scores them with BM25 and TF-IDF cosine similarity, and normalizes those scores into a shared range.",
      },
      {
        title: "5. Quote-aware reranking",
        body:
          "The strongest lexical candidates are reranked with exact phrase detection, proximity scoring, and fuzzy matching so misquotes and near-matches still surface useful results.",
      },
      {
        title: "6. UI delivery",
        body:
          "The Next.js frontend submits a search request to an internal API route, which proxies the request to Flask and returns JSON results back to the browser UI.",
      },
    ],
  },
  {
    title: "How Search Is Implemented",
    columns: "lg:grid-cols-3",
    items: [
      {
        title: "Passage indexing",
        body:
          "Instead of indexing one full transcript as one document, QueryQuote splits each movie into sliding passages. That improves recall for short lines and keeps the ranking focused on the most relevant quote-sized region.",
      },
      {
        title: "Hybrid scoring",
        body:
          "The retrieval layer combines BM25 and TF-IDF cosine similarity using weighted score blending. That gives the system a strong lexical baseline before any quote-specific heuristics are applied.",
      },
      {
        title: "Quote reranking",
        body:
          "The final reranking stage checks whether the exact phrase appears, how tightly the query terms occur together, and how similar the remembered quote is to the original text using fuzzy matching.",
      },
    ],
  },
  {
    title: "Request Flow",
    columns: "md:grid-cols-4",
    items: [
      { body: "The user types a quote into /search and selects a top-k result count." },
      { body: "The browser sends the request to /api/search inside the Next.js app." },
      { body: "The Next.js route forwards the request to the Flask backend at /api/search." },
      { body: "Flask runs the search engine and returns ranked passages back to the UI." },
    ],
  },
  {
    title: "Code Map",
    columns: "lg:grid-cols-2",
    items: [
      {
        title: "Frontend routes",
        list: [
          "/app/(home)/page.jsx for the landing page",
          "/app/(routes)/search/page.jsx for the search experience",
          "/app/(routes)/how/page.jsx for this implementation guide",
          "/app/api/search/route.js for the server-side proxy between Next.js and Flask",
        ],
      },
      {
        title: "Backend search core",
        list: [
          "/backend/src/queryquote/passages.py for transcript collection and passage splitting",
          "/backend/src/queryquote/preprocessing.py for tokenization and normalization",
          "/backend/src/queryquote/indexing.py for the in-memory index bundle",
          "/backend/src/queryquote/db_index.py for SQLite index build and search",
          "/backend/src/queryquote/search_engine.py for lexical scoring and reranking",
          "/backend/src/queryquote/quote_matching.py for phrase, proximity, and fuzzy logic",
          "/backend/src/queryquote/ranking.py for BM25, TF-IDF, and score normalization",
          "/backend/src/queryquote/webapp.py for Flask API endpoints",
        ],
      },
    ],
  },
  {
    title: "Current State",
    columns: "md:grid-cols-2",
    items: [
      {
        title: "Already implemented",
        body:
          "The current project already includes index building, a reusable search engine, a Flask API, a Next.js proxy route, and a working quote-search interface in the browser.",
      },
      {
        title: "Why this architecture",
        body:
          "The split between Next.js and Flask keeps the frontend flexible while the retrieval logic stays isolated in Python, which is where the indexing, ranking, and evaluation tools already live.",
      },
    ],
  },
];

function renderCard(item, index) {
  return (
    <article key={item.title ?? item.body ?? index} className="rounded-2xl border border-white/10 bg-white/5 p-5">
      {item.title ? <h3 className="text-base font-semibold text-white">{item.title}</h3> : null}
      {item.body ? (
        <p className={`${item.title ? "mt-3" : ""} text-sm leading-7 text-white/78`}>{item.body}</p>
      ) : null}
      {item.list ? (
        <ul className="mt-4 space-y-3 text-sm leading-7 text-white/78">
          {item.list.map((entry) => (
            <li key={entry}>{entry}</li>
          ))}
        </ul>
      ) : null}
    </article>
  );
}

export default function HowPage() {
  return (
    <main className="h-screen snap-y snap-mandatory overflow-y-auto px-6 py-8 md:px-8 md:py-10">
      <div className="mx-auto max-w-6xl">
        <RouteBackLink />

        <div className="mt-10 grid min-h-[calc(100vh-8rem)] snap-end items-start gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <header className="max-w-3xl">
            <p className="text-xs uppercase tracking-[0.3em] text-white/55">Inside QueryQuote</p>
            <h1 className={`${movieFont.className} mt-3 text-4xl tracking-wide text-white md:text-6xl`}>
              How QueryQuote Works
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-white/78 md:text-base">
              QueryQuote is a movie-quote search engine built to recover the right film even
              when a user remembers only part of a line, drops punctuation, or misquotes the
              wording. The system combines a Next.js frontend, a Flask API, and a retrieval
              pipeline designed specifically for quote lookup.
            </p>
          </header>

          <aside className="rounded-3xl border border-blue-400/20 bg-blue-500/10 p-6">
            <p className="text-xs uppercase tracking-[0.25em] text-blue-200/75">At a glance</p>
            <div className="mt-5 grid gap-4">
              {overviewItems.map(([label, value]) => (
                <div key={label} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-white/45">{label}</p>
                  <p className="mt-2 text-sm leading-6 text-white/90">{value}</p>
                </div>
              ))}
            </div>
          </aside>
        </div>

        <div className="mt-8 grid gap-6">
          {sections.map((section) => (
            <section
              key={section.title}
              className="min-h-[calc(100vh-8rem)] snap-center rounded-3xl border border-white/12 bg-black/35 p-6 md:p-8"
            >
              <h2 className="text-xl font-semibold text-white/95">{section.title}</h2>
              <div className={`mt-5 grid gap-4 ${section.columns}`}>
                {section.items.map(renderCard)}
              </div>
            </section>
          ))}
        </div>
      </div>
    </main>
  );
}
