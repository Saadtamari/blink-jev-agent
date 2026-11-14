import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/nav";

export const metadata: Metadata = {
  title: "Blink · the LLM plans, Jev clicks",
  description: "A fast web agent: an LLM plans, Jev executes every step from screenshots, in parallel tabs.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <Nav />
        <main className="mx-auto max-w-[1600px] px-4 py-6 sm:px-6">{children}</main>
      </body>
    </html>
  );
}
