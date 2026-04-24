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
// export const viewport = {
  // themeColor: "#000000",
// };
export default function RootLayout({ children }) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-screen relative text-white">
        <Background/>
        <div className="relative z-10">
          {children}
        </div>
      </body>
    </html>
  );
}

const Background = () => (
  <>
    <div className="absolute inset-0 bg-[url('/background.png')] bg-cover bg-center bg-no-repeat bg-fixed blur-md" />
    <div className="absolute inset-0 bg-black/70" />
  </>
);
