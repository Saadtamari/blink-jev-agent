"use client";

import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { getJSON } from "@/lib/api";
import { DotPattern } from "@/components/ui/dot-pattern";
import { NumberTicker } from "@/components/ui/number-ticker";

type AgentRes = { success: boolean; time_s: number; cost: number; jev_calls: number; llm_calls: number; steps: number; error?: string | null };
type Row = { id: string; goal: string; repeat: number; blink?: AgentRes; baseline?: AgentRes };
type Summ = { mean_time_s: number; median_time_s: number; mean_cost: number; success_rate: number; mean_llm_calls: number; mean_jev_calls: number };
type Results = { tasks: Row[]; summary: null | { n: number; blink?: Summ; baseline?: Summ; speedup?: number; cost_ratio?: number }; generated?: number };

export default function Benchmark() {
  const [data, setData] = useState<Results | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    getJSON<Results>("/benchmark/results").then(setData).catch(() => setErr("Can't reach the backend."));
  }, []);

  if (err) return <div className="text-rose-300">{err}</div>;
  if (!data) return <div className="text-slate-400">Loading…</div>;
  if (!data.tasks.length)
    return (
      <div className="space-y-2">
        <h1 className="text-2xl font-bold text-white">Benchmark</h1>
        <p className="text-slate-400">No results yet. Run it from backend/:</p>
        <pre className="rounded-lg bg-slate-900 p-3 text-sm text-slate-200">.venv/Scripts/python benchmark/run_benchmark.py</pre>
      </div>
    );

  const s = data.summary!;
  const maxTime = Math.max(...data.tasks.flatMap((t) => [t.blink?.time_s || 0, t.baseline?.time_s || 0]), 1);
  const maxCost = Math.max(...data.tasks.flatMap((t) => [t.blink?.cost || 0, t.baseline?.cost || 0]), 0.0001);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-white">Blink vs an LLM-only agent</h1>
        <p className="mt-1 text-sm text-slate-400">{s.n} live tasks, measured on this machine. Same models and site hints for both agents, run one at a time.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Big k={s.speedup && s.speedup < 1 ? "Slower" : "Faster"} value={s.speedup ? (s.speedup >= 1 ? s.speedup : 1 / s.speedup) : 0} decimals={1} suffix="×" tone="text-sky-300"
          sub={s.blink && s.baseline ? `${s.blink.mean_time_s.toFixed(1)} s vs ${s.baseline.mean_time_s.toFixed(1)} s per task` : ""} />
        <Big k="Cheaper" value={s.cost_ratio || 0} decimals={1} suffix="×" tone="text-emerald-300"
          sub={s.blink && s.baseline ? `$${s.blink.mean_cost.toFixed(4)} vs $${s.baseline.mean_cost.toFixed(4)} per task` : ""} />
        <Big k="Blink success" value={s.blink ? Math.round(s.blink.success_rate * 100) : 0} suffix="%" tone="text-white"
          sub={s.baseline ? `LLM-only: ${Math.round(s.baseline.success_rate * 100)}%` : ""} />
        <Big k="LLM calls per task" value={s.blink ? s.blink.mean_llm_calls : 0} decimals={1} tone="text-amber-300"
          sub={s.baseline ? `LLM-only: ${s.baseline.mean_llm_calls.toFixed(1)} · Blink also uses ${s.blink?.mean_jev_calls.toFixed(1)} Jev calls` : ""} />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Bars title="Time per task (s)" rows={data.tasks} pick={(r) => r?.time_s} max={maxTime} fmt={(v) => `${v.toFixed(1)}s`} />
        <Bars title="Cost per task ($)" rows={data.tasks} pick={(r) => r?.cost} max={maxCost} fmt={(v) => `$${v.toFixed(4)}`} />
      </div>
      <div className="flex gap-4 text-xs text-slate-400">
        <span><span className="mr-1 inline-block h-2 w-3 rounded bg-sky-400" />Blink</span>
        <span><span className="mr-1 inline-block h-2 w-3 rounded bg-amber-400" />LLM-only</span>
        <span>✓ / ✗ = task success check</span>
      </div>
    </div>
  );
}

function Big({ k, value, decimals = 0, suffix = "", tone, sub }: {
  k: string; value: number; decimals?: number; suffix?: string; tone: string; sub: string;
}) {
  return (
    <div className="relative overflow-hidden rounded-xl border border-white/10 bg-slate-950/70 p-5">
      <DotPattern className="text-slate-700/50 [mask-image:radial-gradient(220px_circle_at_top_right,white,transparent)]" />
      <div className="relative text-xs font-medium text-slate-400">{k}</div>
      <div className={`relative mt-1 text-5xl font-semibold tracking-tight tabular-nums ${tone}`}>
        <NumberTicker value={value} decimalPlaces={decimals} className={`tabular-nums ${tone}`} />{suffix}
      </div>
      <div className="relative mt-2 text-xs text-slate-500">{sub}</div>
    </div>
  );
}

function Bars({ title, rows, pick, max, fmt }: {
  title: string; rows: Row[]; pick: (r?: AgentRes) => number | undefined; max: number; fmt: (v: number) => string;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-slate-950/60 p-4">
      <div className="mb-3 text-sm font-semibold text-slate-200">{title}</div>
      <div className="space-y-2">
        {rows.map((r, i) => (
          <div key={i} className="grid grid-cols-[140px_1fr] items-center gap-3 text-xs">
            <div className="truncate text-slate-300" title={r.goal}>{r.id}</div>
            <div className="space-y-0.5">
              {(["blink", "baseline"] as const).map((a) => {
                const v = pick(r[a]);
                if (v === undefined) return null;
                return (
                  <div key={a} className="flex items-center gap-2">
                    <motion.div className={`h-2.5 rounded-full ${a === "blink" ? "bg-sky-400" : "bg-amber-400"}`} initial={{ width: 0 }} animate={{ width: `${Math.max(1, (v / max) * 100)}%` }} transition={{ duration: 0.8, delay: i * 0.05, ease: "easeOut" }} />
                    <span className="whitespace-nowrap tabular-nums text-slate-400">{fmt(v)} {r[a]?.success ? "✓" : "✗"}</span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
