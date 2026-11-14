import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/nav";
import { Ambient } from "@/components/ambient";

export const metadata: Metadata = {
  title: "Blink · the LLM plans, Jev clicks",
  description: "A fast web agent: an LLM plans, Jev executes every step from screenshots, in parallel tabs.",
};

// apply the saved theme before the first paint (no flash); dark by default
const THEME_SCRIPT = `try{var t=localStorage.getItem('blink-theme');document.documentElement.classList.add(t==='light'?'light':'dark')}catch(e){document.documentElement.classList.add('dark')}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="min-h-screen antialiased">
        <Ambient />
        <Nav />
        <main className="mx-auto max-w-[1600px] px-4 py-6 sm:px-6">{children}</main>
      </body>
    </html>
  );
}
