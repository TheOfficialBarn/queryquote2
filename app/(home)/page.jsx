/**
 * Authors: Aiden Barnard & Atharva Patil
 * Assignment: 767 IR Project (Movie Dataset Search Engine)
 * 
 * 
 * Prologue:
 * Home landing page / about page. Brief description of project w/ a continue button
 * 
 * Last updated: 2026-04-23 - Updated both curved marquee rails to neutral-800/90 text color.
 */

import { Jersey_10 } from "next/font/google"; // Our QueryQuote font
import Link from "next/link"; // Next.js version of <a>

// Initializing font variable
const movieFont = Jersey_10({
  weight: ["400"],
  subsets: ["latin"],
});

// Movie text that scrolls w/ marquee styling
const marqueeMovies = [
  "The Dark Knight",
  "Pulp Fiction",
  "The Matrix",
  "Inception",
  "Forrest Gump",
  "Interstellar",
  "The Godfather",
];
const marqueeText = `${marqueeMovies.join("  •  ")}  •  ${marqueeMovies.join("  •  ")}  •  `;

// Wavy marquee text
// Coauthored by ChatGPT (5.5)
function WavyMarquee({ className = "", reverse = false }) {
  return (
    <div className={`w-screen overflow-hidden ${className}`}>
      <svg
        viewBox="0 0 1600 220"
        className="h-40 w-full md:h-44"
        role="img"
        aria-label="Scrolling curved movie titles"
      >
        <defs>
          <path
            id="movie-wave-path"
            d="M 0 112 C 120 45, 280 45, 400 112 C 520 179, 680 179, 800 112 C 920 45, 1080 45, 1200 112 C 1320 179, 1480 179, 1600 112"
          />
        </defs>
        <text className={`${movieFont.className} fill-neutral-800/90`} fontSize="76" letterSpacing="1.5">
          <textPath href="#movie-wave-path" startOffset="0%">
            {marqueeText}
            <animate
              attributeName="startOffset"
              from={reverse ? "-100%" : "0%"}
              to={reverse ? "0%" : "-100%"}
              dur="26s"
              repeatCount="indefinite"
            />
          </textPath>
        </text>
      </svg>
    </div>
  );
}

export default function Home() {
  return (
    <div>
      <main className="relative min-h-screen px-6 py-36 flex flex-col items-center justify-center text-center overflow-hidden">
        <WavyMarquee className="pointer-events-none absolute top-8 left-1/2 -translate-x-1/2" />
        <WavyMarquee className="pointer-events-none absolute bottom-8 left-1/2 -translate-x-1/2" reverse />

        <h1 className={`${movieFont.className} text-6xl md:text-8xl mb-6 tracking-wide`}>
          <span className="bg-linear-to-r from-blue-700 via-purple-700 to-indigo-800 bg-clip-text text-transparent">
            Query Quote
          </span>
        </h1>
        <p className="text-lg max-w-xl mb-8">
          Welcome to <span className={`${movieFont.className} text-2xl bg-linear-to-r from-blue-700 via-purple-700 to-indigo-800 bg-clip-text text-transparent`}>Query Quote</span>, a movie-quote search engine built to find your favorite movies when it&apos;s on the tip of your tongue. Try it today!
        </p>

        <Link
          href="/search"
          className="bg-neutral-800/90 px-4 py-2 rounded-full font-bold hover:bg-neutral-500/90 transition-colors duration-500"
        >
          Continue
        </Link>
      </main>
    </div>
  );
}
