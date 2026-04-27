"use client";

/**
 * Authors: Aiden Barnard & Atharva Patil
 * Assignment: 767 IR Project (Movie Dataset Search Engine)
 * 
 * Prologue:
 * Simple "back" button w/ customiazable href and label
 * 
 * Last updated: 2026-04-27 - Marked the reusable back link as client-safe so
 * interactive route pages can keep using the same navigation component.
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
