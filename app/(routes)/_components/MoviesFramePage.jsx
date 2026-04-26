/**
 * Prologue:
 * Shared embedded movies page used by both the public movies routes.
 * The page keeps the external listing inside the app shell while preserving a
 * consistent back control and panel styling with the other secondary routes.
 * Last updated: 2026-04-25 - Switched the embedded source from Regal to Rotten
 * Tomatoes so the route points at a broader "movies in theaters" listing.
 */
import RouteBackLink from "./RouteBackLink";

export default function MoviesFramePage() {
  return (
    <main className="min-h-screen px-6 py-8 md:px-8 md:py-10">
      <div className="mx-auto max-w-6xl">
        <RouteBackLink />

        <section className="mt-10 rounded-3xl border border-white/12 bg-black/35 p-4 md:p-6">
          <div className="mb-4">
            <p className="text-xs uppercase tracking-[0.3em] text-white/55">Now Playing</p>
            <h1 className="mt-3 text-3xl font-semibold text-white md:text-4xl">Movies Out Now</h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-white/78">
              Browse Rotten Tomatoes' current in-theaters listing without leaving QueryQuote.
            </p>
          </div>

          <div className="overflow-hidden rounded-2xl border border-white/10 bg-black/50">
            <iframe
              title="Movies Out Now"
              src="https://www.rottentomatoes.com/browse/movies_in_theaters/"
              className="h-[75vh] w-full"
              loading="lazy"
              referrerPolicy="strict-origin-when-cross-origin"
            />
          </div>
        </section>
      </div>
    </main>
  );
}
