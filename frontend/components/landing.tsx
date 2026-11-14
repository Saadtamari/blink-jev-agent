"use client";

import { Coins, Crosshair, Gauge, ShieldCheck, Zap } from "lucide-react";
import { BentoGrid, BentoGridItem } from "@/components/ui/bento-grid";
import { DotPattern } from "@/components/ui/dot-pattern";
import { NumberTicker } from "@/components/ui/number-ticker";
import { Architecture } from "@/components/architecture";
import { cn } from "@/lib/utils";

function Stat({ value, decimals = 0, suffix, prefix, label, tone }: {
  value: number; decimals?: number; suffix?: string; prefix?: string; label: string; tone: string;
}) {
  return (
    <div className="relative flex h-full min-h-28 flex-1 flex-col justify-end overflow-hidden rounded-lg border border-white/5 bg-slate-950/60 p-4">
      <DotPattern className="text-slate-700/40 [mask-image:radial-gradient(180px_circle_at_top_right,white,transparent)]" />
      <div className={cn("relative text-4xl font-semibold tracking-tight tabular-nums", tone)}>
        {prefix}<NumberTicker value={value} decimalPlaces={decimals} className={cn("tabular-nums", tone)} />{suffix}
      </div>
      <div className="relative mt-1 text-xs text-slate-400">{label}</div>
    </div>
  );
}

/** Shown before a run starts: how Blink works + measured results. */
export function Landing() {
  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-white/10 bg-slate-950/40 backdrop-blur-sm">
        <div className="flex items-center justify-between border-b border-white/5 px-5 py-3">
          <div className="label-mono text-slate-300">How Blink works</div>
          <div className="hidden text-xs text-slate-500 sm:block">The LLM thinks once. Jev makes every on-screen decision.</div>
        </div>
        <Architecture />
      </section>

      <BentoGrid className="max-w-none md:auto-rows-[15rem]">
        <BentoGridItem
          className="border-white/10 bg-slate-950/40 backdrop-blur-sm md:col-span-2"
          header={<div className="flex gap-3"><Stat value={7.4} decimals={1} suffix="×" label="faster than an LLM-only agent" tone="text-sky-300" />
            <Stat value={3.1} decimals={1} suffix="×" label="cheaper per task" tone="text-emerald-300" /></div>}
          icon={<Gauge className="size-4 text-sky-300" />}
          title={<span className="text-slate-100">Measured on live websites</span>}
          description={<span className="text-slate-400">6 benchmark tasks, same models, one agent at a time. 83% success vs 67%.</span>}
        />
        <BentoGridItem
          className="border-white/10 bg-slate-950/40 backdrop-blur-sm"
          header={<Stat value={0.4} decimals={1} suffix=" s" label="per Jev decision · 8/8 boxes correct" tone="text-emerald-300" />}
          icon={<Crosshair className="size-4 text-emerald-300" />}
          title={<span className="text-slate-100">One call, four answers</span>}
          description={<span className="text-slate-400">Did it work? What page is this? Is the target there? Where is it?</span>}
        />
        <BentoGridItem
          className="border-white/10 bg-slate-950/40 backdrop-blur-sm"
          header={<Stat value={4} label="tabs working in parallel" tone="text-slate-100" />}
          icon={<Zap className="size-4 text-amber-300" />}
          title={<span className="text-slate-100">Parallel by design</span>}
          description={<span className="text-slate-400">The planner splits the goal into independent branches, each in its own tab.</span>}
        />
        <BentoGridItem
          className="border-white/10 bg-slate-950/40 backdrop-blur-sm"
          header={<Stat value={0.012} decimals={3} prefix="$" label="for a full Japan trip answer, FX read live from Wise" tone="text-slate-100" />}
          icon={<Coins className="size-4 text-sky-300" />}
          title={<span className="text-slate-100">Numbers you can trust</span>}
          description={<span className="text-slate-400">Every price has a source link. Missing data says &quot;not found&quot;.</span>}
        />
        <BentoGridItem
          className="border-white/10 bg-slate-950/40 backdrop-blur-sm"
          header={<div className="flex h-full min-h-28 flex-col justify-center gap-2 rounded-lg border border-white/5 bg-slate-950/60 p-4 text-sm">
            <div className="flex items-center gap-2 text-fuchsia-300"><span className="size-2 rounded-full bg-fuchsia-400" />Bot check → your turn</div>
            <div className="flex items-center gap-2 text-orange-300"><span className="size-2 rounded-full bg-orange-400" />Payment page → hard stop</div>
          </div>}
          icon={<ShieldCheck className="size-4 text-fuchsia-300" />}
          title={<span className="text-slate-100">Safe by default</span>}
          description={<span className="text-slate-400">Never solves CAPTCHAs, never logs in, never pays.</span>}
        />
      </BentoGrid>
    </div>
  );
}
