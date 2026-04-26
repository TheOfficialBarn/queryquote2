/**
 * Prologue:
 * Alias route for the embedded "Movies Out Now" experience.
 * Keeping this alias avoids broken navigation if the route name changes or is
 * referenced interchangeably elsewhere in the app.
 * Last updated: 2026-04-25 - Added an alias page that reuses the shared movies frame.
 */
import MoviesFramePage from "../_components/MoviesFramePage";

export default function MoviesNowPage() {
  return <MoviesFramePage />;
}
