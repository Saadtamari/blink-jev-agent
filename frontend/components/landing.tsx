"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { NumberTicker } from "@/components/ui/number-ticker";
import { Architecture } from "@/components/architecture";
import { cn } from "@/lib/utils";

/* ---------- shared building blocks ---------- */

function Section({ eyebrow, title, sub, children }: { eyebrow: string; title: string; sub: string; children: React.ReactNode }) {
  return (
    <section className="space-y-8">
      <div className="max-w-2xl space-y-3">
        <div className="label-mono text-slate-500">{eyebrow}</div>
        <h2 className="text-3xl font-medium tracking-tight text-white sm:text-5xl">{title}</h2>
        <p className="text-base text-slate-400 sm:text-lg">{sub}</p>
      </div>
      {children}
    </section>
  );
}

/** Card shell: soft dot grid inside, a hairline highlight on top, optional accent. */
function Card({ children, accent, className }: { children: React.ReactNode; accent?: boolean; className?: string }) {
  return (
    <div className={cn(
      "group relative overflow-hidden rounded-2xl border bg-slate-950/60 backdrop-blur-sm transition-colors duration-300",
      accent ? "border-emerald-400/30 shadow-[0_0_60px_-24px_rgba(16,185,129,0.45)]" : "border-white/10 hover:border-white/20",
      className)}>
      <div className="pointer-events-none absolute inset-0 opacity-50 [background-image:radial-gradient(var(--dot)_1px,transparent_1.2px)] [background-size:14px_14px] [mask-image:linear-gradient(to_bottom,black,transparent_70%)]" />
      <div className={cn("pointer-events-none absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent to-transparent",
        accent ? "via-emerald-400/70" : "via-white/25")} />
      <div className="relative">{children}</div>
    </div>
  );
}

function Rows({ rows }: { rows: [string, string, string?][] }) {
  return (
    <div className="divide-y divide-white/10 overflow-hidden rounded-xl border border-white/10 bg-slate-950/70 font-mono text-[12px]">
      {rows.map(([k, v, tone]) => (
        <div key={k + v} className="flex items-center justify-between gap-4 px-3.5 py-2.5">
          <span className={tone || "text-slate-500"}>{k}</span>
          <span className="truncate text-right font-medium text-slate-100">{v}</span>
        </div>
      ))}
    </div>
  );
}

/* ---------- 1. stats strip ---------- */

function StatsStrip() {
  const stats = [
    { v: 7.4, d: 1, s: "×", label: "faster than an LLM-only agent", tone: "text-white" },
    { v: 3.1, d: 1, s: "×", label: "cheaper per task", tone: "text-white" },
    { v: 83, d: 0, s: "%", label: "tasks answered (LLM-only: 67%)", tone: "text-white" },
    { v: 0.4, d: 1, s: " s", label: "per Jev decision · 8/8 boxes correct", tone: "text-emerald-300" },
  ];
  return (
    <div className="grid grid-cols-2 overflow-hidden rounded-2xl border border-white/10 bg-slate-950/50 backdrop-blur-sm lg:grid-cols-4">
      {stats.map((x, i) => (
        <div key={x.label} className={cn("px-6 py-6 sm:px-8", i % 2 === 1 && "border-l border-white/10",
          i >= 2 && "border-t border-white/10 lg:border-t-0", i === 2 && "lg:border-l")}>
          <div className={cn("text-4xl font-medium tracking-tight tabular-nums sm:text-5xl", x.tone)}>
            <NumberTicker value={x.v} decimalPlaces={x.d} className={cn("tabular-nums", x.tone)} />{x.s}
          </div>
          <div className="mt-2 text-sm text-slate-400">{x.label}</div>
        </div>
      ))}
      <div className="label-mono col-span-2 border-t border-white/10 px-6 py-3 text-slate-500 sm:px-8 lg:col-span-4">
        Measured on 6 live-website tasks · same models for both agents · one agent at a time
      </div>
    </div>
  );
}

/* ---------- 2. three layers (table cards) ---------- */

function Layers() {
  return (
    <div className="grid gap-5 md:grid-cols-3">
      <Card className="p-6">
        <div className="label-mono text-amber-300">Upward · the LLM plans</div>
        <h3 className="mt-3 text-xl font-medium text-white">Thinks once, in ~3 s</h3>
        <div className="mt-5"><Rows rows={[["plan", "goal → 4 branches", "text-amber-300"], ["urls", "direct searches", "text-amber-300"], ["extract", "reads a small crop", "text-amber-300"], ["answer", "table + sources", "text-amber-300"]]} /></div>
        <p className="mt-5 text-sm leading-relaxed text-slate-400">The LLM plans, reads crops, recovers from failures and writes the answer. It is never asked &quot;what next?&quot; on every screenshot.</p>
      </Card>
      <Card accent className="p-6">
        <div className="label-mono text-emerald-300">The executor · Jev 1.14</div>
        <h3 className="mt-3 text-xl font-medium text-white">Every on-screen decision</h3>
        <div className="mt-5"><Rows rows={[["choice", "what page is this?", "text-emerald-300"], ["noul", "is the target there?", "text-emerald-300"], ["box", "where do I click?", "text-emerald-300"], ["noul", "did it work?", "text-emerald-300"]]} /></div>
        <p className="mt-5 text-sm leading-relaxed text-slate-400">Four typed answers with probabilities in one call: about 0.4 s and $0.00015. Under 0.6 confidence, the LLM re-plans the step.</p>
      </Card>
      <Card className="p-6">
        <div className="label-mono text-fuchsia-300">Downward · safety</div>
        <h3 className="mt-3 text-xl font-medium text-white">Hands off, never bypasses</h3>
        <div className="mt-5"><Rows rows={[["bot check", "your turn", "text-fuchsia-300"], ["login", "your turn", "text-fuchsia-300"], ["payment", "hard stop", "text-orange-300"], ["card · password", "never typed", "text-orange-300"]]} /></div>
        <p className="mt-5 text-sm leading-relaxed text-slate-400">Blink pauses that one tab and shows you the browser. The other tabs keep working. If a site stays blocked, it switches to a fallback site.</p>
      </Card>
    </div>
  );
}

/* ---------- 3. feature cards with hover visuals ---------- */

function Visual({ children }: { children: React.ReactNode }) {
  return <div className="relative h-52 overflow-hidden rounded-xl border border-white/10 bg-slate-950/80 p-5">{children}</div>;
}

function WindowBar({ label }: { label: string }) {
  return (
    <div className="mb-4 flex items-center gap-2 border-b border-white/10 pb-3 font-mono text-[11px] text-slate-500">
      <span className="flex gap-1"><i className="size-1.5 rounded-full bg-slate-600" /><i className="size-1.5 rounded-full bg-slate-600" /><i className="size-1.5 rounded-full bg-slate-600" /></span>
      {label}
    </div>
  );
}

function ParallelVisual() {
  const tabs = [["flights", "w-[18%]", "duration-700"], ["hotels", "w-[30%]", "duration-1000"], ["costs", "w-[12%]", "duration-500"], ["visa", "w-[24%]", "duration-[1300ms]"]];
  return (
    <Visual>
      <WindowBar label="blink.run(4 tabs)" />
      <div className="space-y-3.5">
        {tabs.map(([name, w, d]) => (
          <div key={name} className="grid grid-cols-[64px_1fr_14px] items-center gap-3 font-mono text-[11px]">
            <span className="text-slate-400">{name}</span>
            <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
              <div className={cn("h-full rounded-full bg-emerald-400 transition-all ease-out group-hover:w-full", w, d)} />
            </div>
            <span className={cn("text-emerald-300 opacity-0 transition-opacity group-hover:opacity-100", d)}>✓</span>
          </div>
        ))}
      </div>
    </Visual>
  );
}

function FxVisual() {
  return (
    <Visual>
      <WindowBar label="wise.read()" />
      <div className="font-mono text-[11px] text-slate-500">prices found in JOD → open a rate tab</div>
      <div className="mt-2 font-mono text-xl text-white">1 JOD = 1.41 USD</div>
      <div className="mt-3 h-px w-full bg-white/10"><div className="h-px w-1/3 bg-sky-400 transition-all duration-700 group-hover:w-full" /></div>
      <div className="mt-4 flex flex-wrap gap-2 font-mono text-[10px]">
        <span className="rounded-md border border-white/10 px-2 py-1 text-slate-400">read by Jev</span>
        <span className="rounded-md border border-white/10 px-2 py-1 text-slate-400">cached 6 h</span>
        <span className="translate-y-1 rounded-md border border-emerald-400/40 px-2 py-1 text-emerald-300 opacity-0 transition-all duration-500 group-hover:translate-y-0 group-hover:opacity-100">totals computed in code ✓</span>
      </div>
    </Visual>
  );
}

function RaceVisual() {
  return (
    <Visual>
      <WindowBar label="race(japan_trip)" />
      <div className="space-y-4 font-mono text-[11px]">
        <div>
          <div className="mb-1.5 flex justify-between"><span className="text-sky-300">Blink</span><span className="text-slate-500 transition-colors group-hover:text-sky-300">16.6 s</span></div>
          <div className="h-2 overflow-hidden rounded-full bg-white/10"><div className="h-full w-[6%] rounded-full bg-sky-400 transition-all duration-500 ease-out group-hover:w-[14%]" /></div>
        </div>
        <div>
          <div className="mb-1.5 flex justify-between"><span className="text-amber-300">LLM-only</span><span className="text-slate-500 transition-colors group-hover:text-amber-300">122.4 s</span></div>
          <div className="h-2 overflow-hidden rounded-full bg-white/10"><div className="h-full w-[6%] rounded-full bg-amber-400 transition-all duration-[2500ms] ease-linear group-hover:w-full" /></div>
        </div>
        <div className="text-slate-500 opacity-0 transition-opacity delay-500 duration-500 group-hover:opacity-100">→ 7.4× faster · 3.1× cheaper</div>
      </div>
    </Visual>
  );
}

function Feature({ visual, eyebrow, title, text, link }: {
  visual: React.ReactNode; eyebrow: string; title: string; text: string; link?: { href: string; label: string };
}) {
  return (
    <Card className="p-3">
      {visual}
      <div className="px-3 pb-3 pt-5">
        <div className="label-mono text-slate-500">{eyebrow}</div>
        <h3 className="mt-2 text-xl font-medium tracking-tight text-white">{title}</h3>
        <p className="mt-2 text-sm leading-relaxed text-slate-400">{text}</p>
        {link && (
          <Link href={link.href} className="mt-4 inline-flex items-center gap-1.5 text-sm text-sky-300 hover:underline">
            {link.label}<ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
          </Link>
        )}
      </div>
    </Card>
  );
}

/* ---------- page ---------- */

/** Shown before a run starts. */
export function Landing() {
  return (
    <div className="space-y-24 pb-20 pt-4">
      <StatsStrip />

      <Section eyebrow="Watch · 60 seconds" title="See Blink in one minute."
        sub="Why web agents are slow today, and how Blink answers the same question with four tabs and Jev doing the clicking.">
        <Card className="p-2 sm:p-3">
          <video src="/blink-demo.mp4" poster="/blink-demo-poster.jpg" controls playsInline preload="metadata"
            className="aspect-video w-full rounded-xl bg-slate-950" aria-label="Blink demo video">
            Your browser can&apos;t play this video. <a href="/blink-demo.mp4">Download it</a>.
          </video>
        </Card>
      </Section>

      <Section eyebrow="How it works" title="One goal in. One answer out."
        sub="The LLM thinks once. Jev makes every on-screen decision, in parallel tabs, and the answer comes back with a source for every number.">
        <Card className="px-2 py-4 sm:px-6"><Architecture /></Card>
      </Section>

      <Section eyebrow="Architecture" title="Three layers, one agent."
        sub="Planning, execution and safety are separate on purpose: each one does the job it is best at.">
        <Layers />
      </Section>

      <Section eyebrow="Why it wins" title="Fast, honest, safe."
        sub="Hover a card to see what happens under the hood.">
        <div className="grid gap-5 md:grid-cols-3">
          <Feature visual={<ParallelVisual />} eyebrow="Parallel · 4 tabs" title="Four tabs at once."
            text="The planner splits your goal into independent branches. Each runs in its own tab, so the slowest site sets the pace, not the sum of all of them." />
          <Feature visual={<FxVisual />} eyebrow="Currency · read, not guessed" title="Numbers you can trust."
            text="Sites show prices in your local currency. Blink opens a rate tab, reads the real rate and converts in code. Missing data says not found." />
          <Feature visual={<RaceVisual />} eyebrow="Measured · live websites" title="Faster than an LLM-only agent."
            text="Same task, same models, run one after the other: Blink finishes in seconds while the screenshot-by-screenshot agent is still clicking."
            link={{ href: "/benchmark", label: "See the benchmark" }} />
        </div>
      </Section>
    </div>
  );
}
