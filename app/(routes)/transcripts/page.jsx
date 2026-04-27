/**
 * Authors: Aiden Barnard & Atharva Patil
 * Assignment: 767 IR Project (Movie Dataset Search Engine)
 * 
 * Prologue:
 * Placeholder transcripts route kept inside the shared app shell.
 * The page currently provides a consistent back affordance while the transcript
 * browsing experience is still being built out.
 * 
 * Last updated: 2026-04-25 - Added the shared back link used by the how and
 * movies pages so secondary routes navigate consistently back to search.
 */

import RouteBackLink from "../_components/RouteBackLink";

export default function Transcripts() {
  return (
    <main className="min-h-screen px-6 py-8 md:px-8 md:py-10">
      <div className="mx-auto max-w-6xl">
        <RouteBackLink />

        <section className="mt-10 rounded-3xl border border-white/12 bg-black/35 p-6 md:p-8">
          <p className="text-xs uppercase tracking-[0.3em] text-white/55">Transcripts</p>
          <h1 className="mt-3 text-3xl font-semibold text-white md:text-4xl">Transcript Browser</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-white/78">
            This route is reserved for transcript browsing and source exploration.
          </p>
        </section>
      </div>
    </main>
  );
}
