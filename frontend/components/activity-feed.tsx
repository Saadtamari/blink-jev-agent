"use client";

import { AnimatePresence, motion } from "motion/react";
import { Brain, Crosshair, Hand, ShieldAlert, Coins, CheckCircle2, ArrowLeftRight } from "lucide-react";
import { AgentState } from "@/lib/useRun";

export type FeedItem = { id: string; ts: number; kind: "jev" | "llm" | "handoff" | "pay" | "fx" | "done" | "switch"; text: string; sub?: string };

const STYLE: Record<FeedItem["kind"], { icon: React.ReactNode; ring: string }> = {
  jev: { icon: <Crosshair className="size-3.5" />, ring: "bg-emerald-500/10 text-emerald-300 ring-emerald-400/30" },
  llm: { icon: <Brain className="size-3.5" />, ring: "bg-amber-500/10 text-amber-300 ring-amber-400/30" },
  handoff: { icon: <Hand className="size-3.5" />, ring: "bg-fuchsia-500/10 text-fuchsia-300 ring-fuchsia-400/30" },
  pay: { icon: <ShieldAlert className="size-3.5" />, ring: "bg-orange-500/10 text-orange-300 ring-orange-400/30" },
  fx: { icon: <Coins className="size-3.5" />, ring: "bg-sky-500/10 text-sky-300 ring-sky-400/30" },
  done: { icon: <CheckCircle2 className="size-3.5" />, ring: "bg-sky-500/10 text-sky-300 ring-sky-400/30" },
  switch: { icon: <ArrowLeftRight className="size-3.5" />, ring: "bg-violet-500/10 text-violet-300 ring-violet-400/30" },
};

const PURPOSE: Record<string, string> = {
  perceive: "read the page", verify: "checked the result", choose: "made a choice",
  plan: "planned the branches", extract: "read prices from a crop", synthesize: "wrote the answer",
  recovery: "re-planned a step", baseline_step: "decided the next click",
};

/** Turns the agent's calls/events into a short, human-readable live feed. */
export function buildFeed(a: AgentState): FeedItem[] {
  const items: FeedItem[] = a.calls.map((c, i) => ({
    id: `c${i}-${c.ts}`, ts: c.ts, kind: c.kind,
    text: `${c.kind === "jev" ? "Jev" : "LLM"} ${PURPOSE[c.purpose] || c.purpose}`,
    sub: `${(c.ms / 1000).toFixed(2)} s · $${(c.cost || 0).toFixed(5)}`,
  }));
  const host = (u: string) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return u; } };
  for (const b of Object.values(a.branches)) {
    for (const [i, sw] of (b.switches || []).entries()) items.push({ id: `sw-${b.id}-${i}`, ts: sw.ts, kind: "switch",
      text: `${b.id}: switched to ${host(sw.to)}`, sub: `${sw.from ? host(sw.from) : "site"} asked for human verification` });
    if (b.handoff) items.push({ id: `h-${b.id}`, ts: b.endedAt || b.startedAt || 0, kind: b.handoff.kind === "payment" ? "pay" : "handoff",
      text: b.handoff.kind === "payment" ? `Stopped before payment on ${b.id}` : `Your turn on ${b.id}`, sub: b.handoff.reason });
    if (b.id.startsWith("fx_") && b.startedAt) items.push({ id: `fx-${b.id}`, ts: b.startedAt, kind: "fx",
      text: `Opened a currency tab: ${b.id.slice(3).replace("_", " → ").toUpperCase()}`, sub: "prices came back in another currency" });
  }
  if (a.final) items.push({ id: "final", ts: a.endedAt || 0, kind: "done", text: "Answer ready", sub: `${a.metrics?.elapsed_s ?? ""} s total` });
  return items.sort((x, y) => y.ts - x.ts).slice(0, 14);
}

export function ActivityFeed({ agent }: { agent: AgentState }) {
  const items = buildFeed(agent);
  return (
    <div className="flex h-full flex-col rounded-xl border border-white/10 bg-slate-950/60">
      <div className="flex items-center justify-between border-b border-white/5 px-4 py-2.5">
        <span className="text-sm font-medium text-slate-200">Live activity</span>
        <span className="text-[11px] text-slate-500">newest first</span>
      </div>
      <div className="relative flex-1 overflow-hidden p-3">
        {!items.length && <div className="py-8 text-center text-xs text-slate-500">Waiting for the first decision…</div>}
        <div className="flex flex-col gap-2">
          <AnimatePresence initial={false}>
            {items.map((it) => (
              <motion.div key={it.id} layout initial={{ opacity: 0, y: -8, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0 }} transition={{ type: "spring", stiffness: 400, damping: 36 }}
                className="flex items-start gap-2.5 rounded-lg border border-white/5 bg-slate-900/60 px-3 py-2">
                <span className={`mt-0.5 grid size-6 shrink-0 place-items-center rounded-md ring-1 ${STYLE[it.kind].ring}`}>{STYLE[it.kind].icon}</span>
                <div className="min-w-0">
                  <div className="truncate text-xs text-slate-200">{it.text}</div>
                  {it.sub && <div className="truncate text-[11px] text-slate-500">{it.sub}</div>}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-slate-950 to-transparent" />
      </div>
    </div>
  );
}
