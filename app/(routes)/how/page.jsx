"use client";

/**
 * Authors: Aiden Barnard & Atharva Patil
 * Assignment: 767 IR Project (Movie Dataset Search Engine)
 *
 * Prologue:
 * QueryQuote "How it Works" page explaining the backend through course-note
 * concepts, with separate V1 and V2 tabs for the two SQLite search pipelines.
 *
 * Last updated: 2026-04-27 - Restored the Query Quote title gradient while
 * keeping the rest of the page on solid non-cyan brand colors.
 */

import { useState } from "react";
import { Jersey_10 } from "next/font/google";
import RouteBackLink from "../_components/RouteBackLink";

const movieFont = Jersey_10({
  weight: ["400"],
  subsets: ["latin"],
});

const queryQuoteTitleColor = "bg-linear-to-r from-blue-700 via-purple-700 to-indigo-800 bg-clip-text text-transparent";

const overviewItems = [
  ["IR Architecture", "Document processing, indexing, query processing, ranking"],
  ["Core Retrieval", "Inverted index, postings, term frequency, document frequency, BM25"],
  ["Quote Matching", "Positions, exact phrases, proximity windows, fuzzy string matching"],
  ["Evaluation", "Qrels, Precision@K, Recall@K, MAP, MRR, nDCG"],
];

const sharedConcepts = [
  {
    title: "Document Processing",
    note: "Lecture 6 IR systems + Lecture 5 text algorithms",
    body:
      "The backend treats transcript files as the document collection, normalizes text, tokenizes it, and splits each movie into overlapping passage windows before indexing.",
  },
  {
    title: "Inverted Index",
    note: "Lecture 3 Boolean retrieval",
    body:
      "Both SQLite engines store term-to-passage postings instead of scanning every transcript at query time. Postings include term frequency and token positions.",
  },
  {
    title: "BM25 Ranking",
    note: "Lecture 4 VSM + BM25",
    body:
      "Candidate passages are scored with BM25-style IDF, term-frequency saturation, and document-length normalization. BM25 is the lexical retrieval baseline.",
  },
  {
    title: "Proximity Search",
    note: "Lecture 5 text algorithms",
    body:
      "Because quotes depend on word order and closeness, the backend stores positions and gives extra score when query terms appear in a tight window.",
  },
  {
    title: "Authority Signal",
    note: "Lecture 4 authority scores + Lecture 9 authority/trust",
    body:
      "The optional authority filter uses vote counts as a query-independent movie-quality signal. It is not PageRank, but it applies the same idea that relevance alone is not always enough.",
  },
  {
    title: "Evaluation",
    note: "Lecture 2 evaluation",
    body:
      "The evaluation module loads queries and qrels, then reports Precision@K, Recall@K, MAP, MRR, and nDCG so ranking changes can be compared with measurable metrics.",
  },
];

const versionDetails = {
  v1: {
    label: "V1",
    title: "SQLite V1: Basic Analyzer + Quote Reranking",
    summary:
      "V1 is the first SQLite search pipeline. It uses the v1 analyzer for lowercase/punctuation-normalized tokens, builds passage-level postings, retrieves with BM25, then reranks with quote-aware signals.",
    rows: [
      {
        title: "Analyzer",
        source: "Lecture 5 tokenization and normalization",
        body:
          "analyzer_v1.py lowercases text, removes punctuation/diacritics, splits on spaces, and removes common stopwords for search/index scoring. Passage splitting keeps stopwords so displayed text remains readable.",
      },
      {
        title: "Index Structure",
        source: "Lecture 3 term-document matrix -> inverted index",
        body:
          "db_index.py stores passages, document lengths, term stats, and postings. Each posting stores passage_id, term frequency, and positions for phrase/proximity scoring.",
      },
      {
        title: "Ranking",
        source: "Lecture 4 BM25 and candidate pruning",
        body:
          "Raw BM25 scores seed candidate passages. Scores are min-max normalized, then exact phrase, proximity, term coverage, fuzzy ratio, and optional authority boosts adjust final rank.",
      },
      {
        title: "What It Avoids",
        source: "Course tradeoff: lexical matching vs. semantic matching",
        body:
          "The backend does not rely on cosine similarity as the main quote matcher because quote search needs word order and closeness, not only vector overlap.",
      },
    ],
  },
  v2: {
    label: "V2",
    title: "SQLite V2: Split Token Streams + Stronger Recovery",
    summary:
      "V2 keeps the same IR foundation but separates phrase-matching tokens from BM25 ranking tokens, adds movie-level phrase postings, and stores authority metadata directly in the index.",
    rows: [
      {
        title: "Analyzer",
        source: "Lecture 5 linguistic preprocessing",
        body:
          "analyzer_v2.py expands contractions, normalizes apostrophes, keeps a full token stream for phrase checks, and filters a BM25 token stream for selective ranking terms.",
      },
      {
        title: "Index Structure",
        source: "Lecture 3 positional postings + Lecture 6 indexing pipeline",
        body:
          "db_index_v2.py stores movies, passages, passage stats, BM25 postings, movie phrase postings, and compact authority fields. Movie phrase postings help recover exact quotes that BM25 alone might miss.",
      },
      {
        title: "Ranking",
        source: "Lecture 8 retrieve -> rerank -> present",
        body:
          "V2 retrieves BM25 candidates, recovers exact phrase candidates, normalizes base scores, then reranks with exact phrase, relaxed content phrase, ordered proximity, coverage, fuzzy matching, and authority.",
      },
      {
        title: "Corpus Experiments",
        source: "Lecture 6 collection architecture",
        body:
          "V2 supports all, intersection, and rest corpus modes so experiments can compare transcripts with authority metadata against transcripts outside that matched set.",
      },
    ],
  },
};

const codeMap = [
  ["analyzer_v1.py", "V1 normalization, tokenization, and stopword filtering"],
  ["analyzer_v2.py", "V2 contraction expansion plus full-token and BM25-token streams"],
  ["passages.py", "Transcript discovery, movie IDs, and overlapping passage windows"],
  ["db_index.py", "SQLite V1 index builder, BM25 retrieval, and quote reranking"],
  ["db_index_v2.py", "SQLite V2 schema, authority metadata, phrase recovery, and reranking"],
  ["authority.py", "Vote-count authority multipliers and title/year matching"],
  ["evaluation.py", "Qrels and ranking metrics from the evaluation lecture"],
  ["webapp.py", "Flask API that exposes health and search endpoints to the frontend"],
];

function ConceptCard({ item }) {
  return (
    <article className="rounded-lg border border-white/10 bg-white/5 p-5">
      <p className="text-xs uppercase tracking-[0.18em] text-purple-200/70">{item.note}</p>
      <h3 className="mt-2 text-base font-semibold text-white">{item.title}</h3>
      <p className="mt-3 text-sm leading-7 text-white/75">{item.body}</p>
    </article>
  );
}

function VersionTab({ detail }) {
  return (
    <div className="mt-6 grid gap-5 lg:grid-cols-[0.8fr_1.2fr]">
      <div className="rounded-lg border border-purple-400/20 bg-indigo-500/10 p-5">
        <p className="text-xs uppercase tracking-[0.22em] text-purple-100/70">{detail.label} pipeline</p>
        <h3 className="mt-3 text-xl font-semibold text-white">{detail.title}</h3>
        <p className="mt-4 text-sm leading-7 text-white/78">{detail.summary}</p>
      </div>

      <div className="grid gap-4">
        {detail.rows.map((row) => (
          <article key={row.title} className="rounded-lg border border-white/10 bg-black/25 p-5">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-baseline sm:justify-between">
              <h4 className="text-base font-semibold text-white">{row.title}</h4>
              <p className="text-xs uppercase tracking-[0.16em] text-white/45">{row.source}</p>
            </div>
            <p className="mt-3 text-sm leading-7 text-white/75">{row.body}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

export default function HowPage() {
  const [activeVersion, setActiveVersion] = useState("v1");
  const activeDetail = versionDetails[activeVersion];

  return (
    <main className="min-h-screen overflow-y-auto px-6 py-8 md:px-8 md:py-10">
      <div className="mx-auto max-w-6xl">
        <RouteBackLink />

        <header className="mt-10 grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-white/55">Inside QueryQuote</p>
            <h1 className={`${movieFont.className} mt-3 text-4xl tracking-wide text-white md:text-6xl`}>
              How <span className={queryQuoteTitleColor}>Query Quote</span> Uses IR
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-white/78 md:text-base">
              The backend turns the final note-sheet concepts into a quote-search pipeline:
              process documents, build positional inverted indexes, retrieve BM25 candidates,
              rerank with quote-specific signals, and evaluate with qrels.
            </p>
          </div>

          <aside className="rounded-lg border border-white/12 bg-black/35 p-5">
            <p className="text-xs uppercase tracking-[0.25em] text-white/50">Cheat-sheet concepts used</p>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              {overviewItems.map(([label, value]) => (
                <div key={label} className="rounded-lg border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-white/45">{label}</p>
                  <p className="mt-2 text-sm leading-6 text-white/88">{value}</p>
                </div>
              ))}
            </div>
          </aside>
        </header>

        <section className="mt-10 rounded-lg border border-white/12 bg-black/35 p-6 md:p-8">
          <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-purple-200/70">Course notes to backend</p>
              <h2 className="mt-2 text-2xl font-semibold text-white">What From The Note Sheets Was Used</h2>
            </div>
            <p className="max-w-xl text-sm leading-7 text-white/65">
              Concepts came mostly from Evaluation, Boolean retrieval, VSM/BM25, Text Algorithms,
              IR Systems, Modern Web Search, and Link Analysis.
            </p>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {sharedConcepts.map((item) => (
              <ConceptCard key={item.title} item={item} />
            ))}
          </div>
        </section>

        <section className="mt-8 rounded-lg border border-white/12 bg-black/35 p-6 md:p-8">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-purple-200/70">Version comparison</p>
              <h2 className="mt-2 text-2xl font-semibold text-white">How V1 And V2 Use The Concepts</h2>
            </div>

            <div className="grid grid-cols-2 rounded-lg border border-white/10 bg-white/5 p-1">
              {Object.entries(versionDetails).map(([key, detail]) => {
                const isActive = key === activeVersion;
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setActiveVersion(key)}
                    className={`rounded-md px-5 py-2 text-sm font-semibold transition ${
                      isActive
                        ? "bg-purple-700 text-white"
                        : "text-white/70 hover:bg-white/10 hover:text-white"
                    }`}
                  >
                    {detail.label}
                  </button>
                );
              })}
            </div>
          </div>

          <VersionTab detail={activeDetail} />
        </section>

        <section className="mt-8 rounded-lg border border-white/12 bg-black/35 p-6 md:p-8">
          <p className="text-xs uppercase tracking-[0.22em] text-purple-200/70">Implementation map</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">Where Those Ideas Live In Code</h2>
          <div className="mt-6 grid gap-3 md:grid-cols-2">
            {codeMap.map(([file, purpose]) => (
              <div key={file} className="rounded-lg border border-white/10 bg-white/5 p-4">
                <p className="font-mono text-sm text-purple-100">{file}</p>
                <p className="mt-2 text-sm leading-6 text-white/75">{purpose}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
