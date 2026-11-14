"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { API } from "@/lib/api";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/theme-toggle";

const LINKS = [
  { href: "/", label: "Mission control" },
  { href: "/runs", label: "Runs" },
  { href: "/benchmark", label: "Benchmark" },
];

export function Nav() {
  const path = usePathname();
  const [online, setOnline] = useState<boolean | null>(null);
  useEffect(() => {
    const check = () => fetch(`${API}/health`).then((r) => setOnline(r.ok)).catch(() => setOnline(false));
    check();
    const t = setInterval(check, 10000);
    return () => clearInterval(t);
  }, []);

  return (
    <header className="sticky top-0 z-30 border-b border-white/5 bg-background/75 backdrop-blur-md">
      <div className="mx-auto flex max-w-[1600px] items-center gap-6 px-4 py-3 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5" aria-label="Blink home">
          <span className="grid size-7 place-items-center rounded-md bg-white text-[13px] font-semibold text-slate-950">B</span>
          <span className="text-lg font-semibold tracking-tight text-white">Blink</span>
        </Link>
        <nav className="flex items-center gap-1 overflow-x-auto text-sm">
          {LINKS.map((l) => {
            const active = l.href === "/" ? path === "/" : path.startsWith(l.href);
            return (
              <Link key={l.href} href={l.href}
                className={cn("whitespace-nowrap rounded-full px-3 py-1.5 transition", active ? "bg-white/10 text-white" : "text-slate-400 hover:text-white")}>
                {l.label}
              </Link>
            );
          })}
        </nav>
        <div className="ml-auto flex items-center gap-2 text-xs text-slate-400">
          <span className={cn("size-2 rounded-full", online === null ? "bg-slate-500" : online ? "bg-emerald-400" : "bg-rose-400")} />
          <span className="label-mono hidden sm:inline">{online === null ? "Connecting" : online ? "Backend online" : "Backend offline"}</span>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
