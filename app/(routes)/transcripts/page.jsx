"use client";

/**
 * Authors: Aiden Barnard & Atharva Patil
 * Assignment: 767 IR Project (Movie Dataset Search Engine)
 *
 * Prologue:
 * Transcript movie search page with Search-style input, metadata filters, and
 * clickable result cards that route to the dedicated transcript detail page.
 *
 * Last updated: 2026-04-27 - Cleaned up filter chip layout with a contained
 * responsive grid so expanded facets do not create ragged rows.
 */

import { useEffect, useState } from "react";
import { Jersey_10 } from "next/font/google";
import Link from "next/link";
import RouteBackLink from "../_components/RouteBackLink";

const movieFont = Jersey_10({
  weight: ["400"],
  subsets: ["latin"],
});

const transcriptSearchLimit = 50;

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

function formatMovieLabel(movie) {
  return movie.year ? `${movie.title} (${movie.year})` : movie.title;
}

function transcriptHref(movieId) {
  return `/transcripts/${encodeURIComponent(movieId)}`;
}

function decadeLabel(decade) {
  return `${String(decade).slice(0, 3)}0s`;
}

function GroupFilterToggle({ label, count, active, onClick }) {
  const countLabel = count > 0 ? ` ${count}` : "";

  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-4 py-1.5 text-sm font-semibold transition-colors active:scale-95 ${
        active
          ? "border-blue-300/80 bg-blue-400/30 text-white"
          : "border-white/20 bg-white/10 text-white/85 hover:bg-white/20"
      }`}
      aria-pressed={active}
    >
      {label}
      {countLabel ? (
        <span className="ml-1 rounded-full bg-white/15 px-1.5 py-0.5 text-xs">
          {countLabel.trim()}
        </span>
      ) : null}
    </button>
  );
}

function FilterToggle({ option, active, onToggle }) {
  return (
    <button
      type="button"
      onClick={() => onToggle(option)}
      className={`min-h-9 w-full rounded-full border px-3 py-1 text-sm transition-colors active:scale-95 ${
        active
          ? "border-blue-300/80 bg-blue-400/30 text-white"
          : "border-white/20 bg-white/10 text-white/85 hover:bg-white/20"
      }`}
      aria-pressed={active}
    >
      {option.label}
    </button>
  );
}

function TranscriptResultCard({ movie }) {
  const genres = Array.isArray(movie.genres) ? movie.genres : [];

  return (
    <Link href={transcriptHref(movie.movie_id)} className="block">
      <article className="rounded-2xl border border-white/15 bg-black/35 p-4 transition-colors hover:border-blue-300/50 hover:bg-blue-500/10 sm:p-5">
        <p className="text-xs text-blue-300/80">Transcript movie</p>
        <h2 className="mt-1 text-xl text-blue-300">{formatMovieLabel(movie)}</h2>
        {genres.length ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {genres.slice(0, 5).map((genre) => (
              <span
                key={`${movie.movie_id}-${genre}`}
                className="rounded-full border border-white/15 bg-white/10 px-2 py-0.5 text-xs text-white/75"
              >
                {genre}
              </span>
            ))}
          </div>
        ) : null}
        <p className="mt-3 break-all text-xs text-white/55">Movie ID: {movie.movie_id}</p>
        <p className="mt-2 break-all text-xs text-white/45">Source: {movie.source_file}</p>
      </article>
    </Link>
  );
}

function ResultsEmptyState({ errorMessage, hasSearched }) {
  if (!hasSearched) {
    return null;
  }

  return (
    <article className="rounded-2xl border border-white/15 bg-black/35 p-5">
      <h2 className="text-xl text-white">No transcript movies found</h2>
      <p className="mt-2 text-sm text-white/70">
        {errorMessage || "Try a different title, decade, or genre filter."}
      </p>
    </article>
  );
}

export default function Transcripts() {
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [activeDecades, setActiveDecades] = useState([]);
  const [activeGenres, setActiveGenres] = useState([]);
  const [expandedFilterGroup, setExpandedFilterGroup] = useState("decades");
  const [decadeFilterOptions, setDecadeFilterOptions] = useState([]);
  const [genreFilterOptions, setGenreFilterOptions] = useState([]);
  const [movies, setMovies] = useState([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

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
            type: "decade",
            value: String(decade),
          })),
        );

        const genres = Array.isArray(data.genres) ? data.genres : [];
        setGenreFilterOptions(
          genres.map((genre) => ({
            id: `genre-${genre}`,
            label: genre,
            type: "genre",
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

  async function fetchTranscriptMovies({ nextQuery, nextDecades, nextGenres }) {
    const params = new URLSearchParams({
      limit: String(transcriptSearchLimit),
      index_version: "v2",
    });
    if (nextQuery.trim()) {
      params.set("q", nextQuery.trim());
    }
    nextDecades.forEach((decade) => params.append("decade", decade));
    nextGenres.forEach((genre) => params.append("genre", genre));

    setHasSearched(true);
    setIsSearching(true);
    setErrorMessage("");

    try {
      const response = await fetch(`/api/transcripts?${params.toString()}`, {
        cache: "no-store",
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.error || "Transcript search failed");
      }

      setMovies(Array.isArray(data.results) ? data.results : []);
    } catch (error) {
      setMovies([]);
      setErrorMessage(error instanceof Error ? error.message : "Transcript search failed");
    } finally {
      setIsSearching(false);
    }
  }

  function handleSearch(event) {
    event.preventDefault();
    const nextQuery = query.trim();
    setSubmittedQuery(nextQuery);
    fetchTranscriptMovies({
      nextQuery,
      nextDecades: activeDecades,
      nextGenres: activeGenres,
    });
  }

  function handleToggle(option) {
    const toggleValue = (values, nextValue) =>
      values.includes(nextValue)
        ? values.filter((value) => value !== nextValue)
        : [...values, nextValue];

    const resolvedDecades =
      option.type === "decade"
        ? toggleValue(activeDecades, option.value)
        : activeDecades;
    const resolvedGenres =
      option.type === "genre"
        ? toggleValue(activeGenres, option.value)
        : activeGenres;

    setActiveDecades(resolvedDecades);
    setActiveGenres(resolvedGenres);
    fetchTranscriptMovies({
      nextQuery: submittedQuery || query.trim(),
      nextDecades: resolvedDecades,
      nextGenres: resolvedGenres,
    });
  }

  function clearFilters() {
    setActiveDecades([]);
    setActiveGenres([]);
    fetchTranscriptMovies({
      nextQuery: submittedQuery || query.trim(),
      nextDecades: [],
      nextGenres: [],
    });
  }

  const resultSummary = isSearching
    ? "Searching transcript movies..."
    : `${movies.length} transcript movie${movies.length === 1 ? "" : "s"} found`;
  const visibleFilterOptions =
    expandedFilterGroup === "decades" ? decadeFilterOptions : genreFilterOptions;
  const hasActiveFilters = activeDecades.length > 0 || activeGenres.length > 0;

  return (
    <main className="min-h-screen px-6 py-8 md:px-8 md:py-10">
      <div className="mx-auto max-w-5xl">
        <RouteBackLink />

        <section className="mx-auto mt-14 max-w-3xl text-center">
          <p className="text-xs uppercase tracking-[0.25em]">
            <span className="bg-linear-to-r from-blue-700 via-purple-700 to-indigo-800 bg-clip-text text-transparent">
              Query Quote
            </span>
          </p>
          <h1 className={`${movieFont.className} mt-2 text-5xl tracking-wide md:text-6xl`}>
            Find A Transcript
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-white/80">
            Search the indexed movie dataset by title, then narrow results by release decade or Metacritic genre.
          </p>

          <form className="mt-8" onSubmit={handleSearch}>
            <div className="flex items-center gap-2 rounded-full bg-white p-1 text-black transition-shadow duration-150 focus-within:ring-2 focus-within:ring-blue-500/80 focus-within:ring-offset-2 focus-within:ring-offset-transparent">
              <SearchIcon />
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search for a movie..."
                className="min-w-0 flex-1 bg-transparent outline-none placeholder:text-black/45"
                autoComplete="off"
              />
              <button
                type="submit"
                disabled={isSearching || (!query.trim() && !hasActiveFilters)}
                className="rounded-full bg-black p-3 font-semibold tracking-tight text-white transition-all duration-150 hover:bg-neutral-950 active:scale-95 disabled:cursor-not-allowed disabled:bg-neutral-700"
              >
                {isSearching ? "Searching..." : "Search"}
              </button>
            </div>
          </form>

          <div className="mt-4 flex flex-wrap justify-center gap-2">
            <GroupFilterToggle
              label="Decades"
              count={activeDecades.length}
              active={expandedFilterGroup === "decades"}
              onClick={() => setExpandedFilterGroup("decades")}
            />
            <GroupFilterToggle
              label="Genres"
              count={activeGenres.length}
              active={expandedFilterGroup === "genres"}
              onClick={() => setExpandedFilterGroup("genres")}
            />
            {hasActiveFilters ? (
              <button
                type="button"
                onClick={clearFilters}
                className="rounded-full border border-white/20 bg-white/5 px-3 py-1 text-sm text-white/70 transition-colors hover:bg-white/15"
              >
                Clear
              </button>
            ) : null}
          </div>

          <div className="mx-auto mt-3 max-w-4xl rounded-2xl border border-white/10 bg-black/25 p-3">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
              {visibleFilterOptions.map((option) => {
                const active =
                  option.type === "decade"
                    ? activeDecades.includes(option.value)
                    : activeGenres.includes(option.value);
                return (
                  <FilterToggle
                    key={option.id}
                    option={option}
                    active={active}
                    onToggle={handleToggle}
                  />
                );
              })}
            </div>
          </div>
        </section>

        <section className="mt-8">
          {hasSearched ? (
            <p className="mb-4 text-sm text-white/60">{resultSummary}</p>
          ) : null}
          <div className="space-y-4">
            {movies.length ? (
              movies.map((movie) => (
                <TranscriptResultCard key={movie.movie_id} movie={movie} />
              ))
            ) : !isSearching ? (
              <ResultsEmptyState errorMessage={errorMessage} hasSearched={hasSearched} />
            ) : null}
          </div>
        </section>
      </div>
    </main>
  );
}
