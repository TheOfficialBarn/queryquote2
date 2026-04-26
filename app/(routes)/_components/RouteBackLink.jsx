/**
 * Prologue:
 * Shared back-link control for route pages that need a lightweight return action.
 * Centralizing the link keeps the styling consistent across informational routes.
 * Last updated: 2026-04-25 - Added a reusable back link matching the search page's
 * hover treatment for the how, transcripts, and movies pages.
 */
import Link from "next/link";

export default function RouteBackLink({ href = "/search", label = "← Back" }) {
  return (
    <div className="border-b border-white/10 pb-5">
      <Link
        href={href}
        className="inline-flex items-center text-sm text-white/75 hover:underline hover:text-blue-500"
      >
        {label}
      </Link>
    </div>
  );
}
