/**
 * Prologue:
 * Root application layout for global metadata, fonts, and shared background treatment.
 * The viewport theme color is defined here so browser chrome, including Safari's
 * toolbar tint, reflects the app background instead of falling back to default UI.
 * Last updated: 2026-04-25 - Moved the shared image backdrop to a dedicated fixed
 * layer so the background stays pinned without scroll wobble.
 */
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata = {
  title: "QueryQuote",
  description: "QueryQuote app",
  manifest: "/site.webmanifest",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/favicon-32x32.png", type: "image/png", sizes: "32x32" },
      { url: "/favicon-16x16.png", type: "image/png", sizes: "16x16" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180" }],
    shortcut: ["/favicon.ico"],
  },
};

export default function RootLayout({ children }) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-screen relative bg-[#07091a] text-white">
        <Background />
        <div className="relative z-10">
          {children}
        </div>
      </body>
    </html>
  );
}

const Background = () => (
  <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
    <div className="absolute inset-[-2%] bg-[url('/background.png')] bg-cover bg-center bg-no-repeat blur-sm scale-105" />
    <div className="absolute inset-0 bg-black/70" />
  </div>
);
