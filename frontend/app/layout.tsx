import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Blink — the LLM plans, Jev clicks",
  description: "A fast web agent: an LLM plans, Jev executes every step from screenshots, in parallel tabs.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased">
        <header className="sticky top-0 z-20 border-b border-slate-800 bg-slate-950/90 backdrop-blur">
          <div className="mx-auto flex max-w-[1600px] items-center gap-6 px-6 py-3">
            <Link href="/" className="flex items-baseline gap-2">
              <span className="text-2xl font-black tracking-tight text-white">Blink</span>
              <span className="hidden text-sm text-slate-400 sm:inline">the LLM plans, Jev clicks</span>
            </Link>
            <nav className="flex gap-4 text-sm text-slate-300">
              <Link href="/" className="hover:text-white">Mission control</Link>
              <Link href="/runs" className="hover:text-white">Runs</Link>
              <Link href="/benchmark" className="hover:text-white">Benchmark</Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-[1600px] px-6 py-6">{children}</main>
      </body>
    </html>
  );
}
