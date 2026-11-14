"use client";

import { forwardRef, useRef } from "react";
import { BedDouble, Brain, CircleCheckBig, Crosshair, FileCheck2, Plane, ScrollText, Utensils } from "lucide-react";
import { AnimatedBeam } from "@/components/ui/animated-beam";
import { cn } from "@/lib/utils";

const Node = forwardRef<HTMLDivElement, { className?: string; children: React.ReactNode; label: string; sub?: string }>(
  ({ className, children, label, sub }, ref) => (
    <div className="z-10 flex flex-col items-center gap-2">
      <div ref={ref}
        className={cn("grid size-12 place-items-center rounded-2xl border border-white/10 bg-slate-900 text-slate-200 shadow-[0_0_24px_-8px_rgba(0,0,0,0.8)]", className)}>
        {children}
      </div>
      <div className="text-center leading-tight">
        <div className="text-xs font-medium text-slate-200">{label}</div>
        {sub && <div className="text-[11px] text-slate-500">{sub}</div>}
      </div>
    </div>
  ),
);
Node.displayName = "Node";

/** "Goal -> LLM plans -> Jev executes 4 tabs in parallel -> answer", drawn with animated beams. */
export function Architecture() {
  const container = useRef<HTMLDivElement>(null);
  const goal = useRef<HTMLDivElement>(null);
  const llm = useRef<HTMLDivElement>(null);
  const jev = useRef<HTMLDivElement>(null);
  const t1 = useRef<HTMLDivElement>(null);
  const t2 = useRef<HTMLDivElement>(null);
  const t3 = useRef<HTMLDivElement>(null);
  const t4 = useRef<HTMLDivElement>(null);
  const out = useRef<HTMLDivElement>(null);
  const tabs = [t1, t2, t3, t4];
  const beam = { pathColor: "#94a3b8", pathOpacity: 0.12, pathWidth: 1.5 };

  return (
    <div ref={container} className="relative flex w-full items-center justify-between gap-2 overflow-hidden px-2 py-6 sm:px-6">
      <Node ref={goal} label="Your goal" sub="one sentence"><ScrollText className="size-5" /></Node>
      <Node ref={llm} label="LLM plans" sub="once, ~3 s" className="border-amber-400/30 text-amber-300"><Brain className="size-5" /></Node>
      <Node ref={jev} label="Jev executes" sub="~0.4 s / step" className="size-14 border-emerald-400/40 text-emerald-300"><Crosshair className="size-6" /></Node>
      <div className="z-10 flex flex-col gap-3">
        <Node ref={t1} label="Flights"><Plane className="size-4" /></Node>
        <Node ref={t2} label="Hotels"><BedDouble className="size-4" /></Node>
        <Node ref={t3} label="Daily costs"><Utensils className="size-4" /></Node>
        <Node ref={t4} label="Visa"><FileCheck2 className="size-4" /></Node>
      </div>
      <Node ref={out} label="Answer" sub="with sources" className="border-sky-400/40 text-sky-300"><CircleCheckBig className="size-5" /></Node>

      <AnimatedBeam containerRef={container} fromRef={goal} toRef={llm} {...beam} gradientStartColor="#fbbf24" gradientStopColor="#f59e0b" duration={4} />
      <AnimatedBeam containerRef={container} fromRef={llm} toRef={jev} {...beam} gradientStartColor="#fbbf24" gradientStopColor="#34d399" duration={4} delay={0.4} />
      {tabs.map((t, i) => (
        <AnimatedBeam key={i} containerRef={container} fromRef={jev} toRef={t} {...beam} curvature={(i - 1.5) * -18}
          gradientStartColor="#34d399" gradientStopColor="#10b981" duration={3} delay={0.8 + i * 0.15} />
      ))}
      {tabs.map((t, i) => (
        <AnimatedBeam key={`o${i}`} containerRef={container} fromRef={t} toRef={out} {...beam} curvature={(i - 1.5) * 18}
          gradientStartColor="#10b981" gradientStopColor="#38bdf8" duration={3} delay={1.6 + i * 0.15} />
      ))}
    </div>
  );
}
