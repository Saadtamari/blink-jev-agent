"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

/** Dark / light switch. The choice is stored per browser; the class is set before paint by the script in layout. */
export function ThemeToggle() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    setTheme(document.documentElement.classList.contains("light") ? "light" : "dark");
  }, []);

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    const el = document.documentElement;
    el.classList.remove("dark", "light");
    el.classList.add(next);
    try {
      localStorage.setItem("blink-theme", next);
    } catch {
      /* storage may be blocked: the theme still applies for this visit */
    }
  }

  return (
    <button onClick={toggle} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      className="grid size-8 place-items-center rounded-full border border-white/10 text-slate-300 transition hover:border-white/25 hover:text-white">
      {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </button>
  );
}
