"use client";

import { useEffect, useState } from "react";
import { BranchState, StepRow } from "@/lib/useRun";
import { FinalAnswer, Metrics, fileUrl, money } from "@/lib/api";
import { BorderBeam } from "@/components/ui/border-beam";
import { NumberTicker } from "@/components/ui/number-ticker";

export const PATH_STYLE: Record<string, { label: string; cls: string; stroke: string }> = {
  jev: { label: "Jev", cls: "bg-emerald-500/15 text-emerald-300 ring-emerald-400/40", stroke: "#34d399" },
  dom_fastpath: { label: "DOM", cls: "bg-sky-500/15 text-sky-300 ring-sky-400/40", stroke: "#38bdf8" },
  site_memory: { label: "Memory", cls: "bg-violet-500/15 text-violet-300 ring-violet-400/40", stroke: "#a78bfa" },
  llm_recovery: { label: "LLM", cls: "bg-amber-500/15 text-amber-300 ring-amber-400/40", stroke: "#fbbf24" },
  llm: { label: "LLM", cls: "bg-amber-500/15 text-amber-300 ring-amber-400/40", stroke: "#fbbf24" },
  none: { label: "—", cls: "bg-slate-500/15 text-slate-300 ring-slate-400/30", stroke: "#94a3b8" },
};

const STATUS_STYLE: Record<string, string> = {
  pending: "bg-slate-600/40 text-slate-300",
  running: "bg-blue-500/20 text-blue-300",
  done: "bg-emerald-500/20 text-emerald-300",
  partial: "bg-amber-500/20 text-amber-300",
  failed: "bg-rose-500/20 text-rose-300",
  waiting_user: "bg-fuchsia-500/20 text-fuchsia-300",
  stopped: "bg-orange-500/20 text-orange-300",
};

export function Badge({ path }: { path?: string }) {
  const s = PATH_STYLE[path || "none"] || PATH_STYLE.none;
  return <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ring-1 ${s.cls}`}>{s.label}</span>;
}

export function StatusPill({ status }: { status: string }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[status] || STATUS_STYLE.pending}`}>
      {status.replace("_", " ")}
    </span>
  );
}

export function ConfBar({ value }: { value?: number | null }) {
  if (value === null || value === undefined) return <div className="h-1.5 w-16 rounded bg-slate-700" />;
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  const color = value >= 0.85 ? "bg-emerald-400" : value >= 0.6 ? "bg-amber-400" : "bg-rose-400";
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1.5 w-16 overflow-hidden rounded bg-slate-700">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8 text-right text-[11px] tabular-nums text-slate-300">{(value).toFixed(2)}</span>
    </div>
  );
}

export function useTicker(running: boolean) {
  const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setNow(Date.now() / 1000), 100);
    return () => clearInterval(t);
  }, [running]);
  return now;
}

export function Counters({ label, metrics, startedAt, endedAt, accent }: {
  label: string; metrics?: Metrics; startedAt?: number; endedAt?: number; accent: string;
}) {
  const running = !!startedAt && !endedAt;
  const now = useTicker(running);
  const elapsed = startedAt ? ((endedAt || now) - startedAt) : 0;
  return (
    <div className="flex flex-wrap items-stretch gap-3">
      <div className="min-w-36 rounded-xl border border-white/10 bg-slate-950/60 px-4 py-3">
        <div className={`label-mono flex items-center gap-2 ${accent}`}>
          {running && <span className="size-1.5 animate-pulse rounded-full bg-current" />}{label}
        </div>
        <div className="mt-1 text-4xl font-semibold tracking-tight tabular-nums text-white">{elapsed.toFixed(1)}<span className="text-xl text-slate-400"> s</span></div>
      </div>
      <Stat k="Cost" prefix="$" v={metrics?.total_cost ?? 0} decimals={4} />
      <Stat k="Jev calls" v={metrics?.jev_calls ?? 0} tone="text-emerald-300" />
      <Stat k="LLM calls" v={metrics?.llm_calls ?? 0} tone="text-amber-300" />
      <Stat k="Steps" v={metrics?.steps ?? 0} />
      {metrics?.cache_hits ? <Stat k="Memory hits" v={metrics.cache_hits} tone="text-violet-300" /> : null}
    </div>
  );
}

function Stat({ k, v, prefix = "", decimals = 0, tone = "text-slate-100" }: {
  k: string; v: number; prefix?: string; decimals?: number; tone?: string;
}) {
  return (
    <div className="min-w-24 rounded-xl border border-white/10 bg-slate-950/60 px-4 py-3">
      <div className="label-mono text-slate-500">{k}</div>
      <div className={`mt-1 text-2xl font-semibold tabular-nums ${tone}`}>
        {prefix}{v > 0 ? <NumberTicker value={v} startValue={0} decimalPlaces={decimals} className={`tabular-nums ${tone}`} /> : (0).toFixed(decimals)}
      </div>
    </div>
  );
}

export function BranchTile({ b, viewport, onContinue, compact }: {
  b: BranchState; viewport: { width: number; height: number }; onContinue: (id: string) => void; compact?: boolean;
}) {
  const current = [...b.steps].reverse().find((s) => s.running) || b.steps[b.steps.length - 1];
  const box = b.lastBox && (!b.lastBox.shot || b.lastBox.shot === b.lastShot) ? b.lastBox : undefined;
  const st = PATH_STYLE[box?.used || "jev"] || PATH_STYLE.jev;
  return (
    <div className="relative flex flex-col overflow-hidden rounded-xl border border-white/10 bg-slate-950/70">
      {b.status === "running" && <BorderBeam size={90} duration={5} colorFrom="#34d399" colorTo="#38bdf8" />}
      <div className="flex items-center justify-between gap-2 border-b border-white/10 px-3 py-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-white">{b.id}</div>
          {!compact && <div className="truncate text-xs text-slate-400">{b.goal}</div>}
        </div>
        <StatusPill status={b.status} />
      </div>
      <div className="relative aspect-[1366/900] w-full bg-slate-950">
        {b.lastShot ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={fileUrl(b.lastShot)} alt={`${b.id} tab`} className="absolute inset-0 h-full w-full object-cover object-top" />
        ) : (
          <div className="absolute inset-0 grid place-items-center text-sm text-slate-500">waiting for the first screenshot…</div>
        )}
        {box && b.lastShot && (
          <div className="pointer-events-none absolute rounded-sm"
            style={{
              left: `${(box.x / viewport.width) * 100}%`, top: `${(box.y / viewport.height) * 100}%`,
              width: `${Math.max(1.2, (box.w / viewport.width) * 100)}%`, height: `${Math.max(1.6, (box.h / viewport.height) * 100)}%`,
              border: `3px solid ${st.stroke}`, boxShadow: `0 0 0 4px ${st.stroke}33`,
            }}>
            <span className="absolute -top-6 left-0 whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-bold text-slate-950"
              style={{ background: st.stroke }}>
              {st.label}{box.confidence != null ? ` ${Number(box.confidence).toFixed(2)}` : ""}
            </span>
          </div>
        )}
        {b.handoff && (
          <div className="absolute inset-0 grid place-items-center bg-slate-950/70 p-4">
            <div className={`max-w-sm rounded-xl border p-4 text-center ${b.handoff.kind === "payment" ? "border-orange-400 bg-orange-950/80" : "border-fuchsia-400 bg-fuchsia-950/80"}`}>
              <div className="text-sm font-bold text-white">
                {b.handoff.kind === "payment" ? "Stopped before payment" : "Your turn"}
              </div>
              <div className="mt-1 text-xs text-slate-200">{b.handoff.message}</div>
              {b.handoff.kind !== "payment" ? (
                <button onClick={() => onContinue(b.id)}
                  className="mt-3 rounded-lg bg-fuchsia-500 px-4 py-1.5 text-sm font-semibold text-white hover:bg-fuchsia-400">
                  Continue
                </button>
              ) : b.handoff.url ? (
                <a href={b.handoff.url} target="_blank" rel="noreferrer" className="mt-3 inline-block text-xs text-orange-200 underline">
                  Open the page
                </a>
              ) : null}
            </div>
          </div>
        )}
      </div>
      <div className="flex items-center justify-between gap-2 px-3 py-2 text-xs">
        <div className="min-w-0 truncate text-slate-300">
          {current ? <><span className="font-semibold text-slate-100">{current.step.action}</span> {current.step.target || current.step.value || ""}</> : "starting…"}
        </div>
        {b.switches?.length ? (
          <span className="shrink-0 rounded-full bg-violet-500/10 px-2 py-0.5 text-violet-300" title="The site asked for human verification, so Blink moved to another website">
            switched site ×{b.switches.length}
          </span>
        ) : b.perception && <span className="shrink-0 text-slate-400">page: <span className="text-slate-200">{b.perception.state}</span></span>}
      </div>
    </div>
  );
}

export function StepTimeline({ b }: { b: BranchState }) {
  if (!b.steps.length) return null;
  return (
    <div className="rounded-xl border border-white/10 bg-slate-950/60 p-3">
      <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">{b.id}</div>
      <div className="space-y-1">
        {b.steps.map((s: StepRow, i: number) => (
          <div key={i} className="grid grid-cols-[1fr_auto_auto_auto] items-center gap-2 text-xs">
            <div className="truncate text-slate-200">
              <span className="font-semibold">{s.step.action}</span> <span className="text-slate-400">{s.step.target || s.step.value || ""}</span>
            </div>
            {s.running ? <span className="animate-pulse text-blue-300">running</span> : <Badge path={s.result?.used} />}
            <ConfBar value={s.result?.confidence} />
            <span className={`w-16 text-right tabular-nums ${s.result?.status === "failed" ? "text-rose-300" : s.result?.status === "blocked" ? "text-orange-300" : "text-slate-400"}`}>
              {s.result ? (s.result.status === "ok" ? `${(s.result.duration_ms / 1000).toFixed(1)}s` : s.result.status) : ""}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function FinalAnswerView({ final, title }: { final?: { answer: FinalAnswer | null; error?: string }; title: string }) {
  if (!final) return null;
  const a = final.answer;
  if (!a) return <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-4 text-sm text-rose-200">{title}: {final.error || "no answer"}</div>;
  const t = a.totals as Record<string, any>;
  const cur = (t?.currency as string) || a.table[0]?.currency || "USD";
  return (
    <div className="rounded-xl border border-emerald-400/20 bg-slate-950/70 p-5">
      <div className="text-xs font-semibold uppercase tracking-wider text-emerald-300">{title}</div>
      <p className="mt-2 text-lg leading-relaxed text-white">{a.summary}</p>
      {a.table.length > 0 && (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase text-slate-400">
              <tr><th className="py-1 pr-3">Item</th><th className="pr-3 text-right">Low</th><th className="pr-3 text-right">Mid</th><th className="pr-3 text-right">High</th><th className="pr-3">Note</th><th>Source</th></tr>
            </thead>
            <tbody>
              {a.table.map((r, i) => (
                <tr key={i} className="border-t border-slate-700/60 text-slate-200">
                  <td className="py-1.5 pr-3 font-medium">{r.category}</td>
                  <td className="pr-3 text-right tabular-nums">{money(r.low, r.currency)}</td>
                  <td className="pr-3 text-right tabular-nums font-semibold text-white">{money(r.mid, r.currency)}</td>
                  <td className="pr-3 text-right tabular-nums">{money(r.high, r.currency)}</td>
                  <td className="pr-3 text-xs text-slate-400">{r.note}</td>
                  <td className="text-xs">{r.source_url ? <a className="text-sky-300 underline" href={r.source_url} target="_blank" rel="noreferrer">link</a> : "–"}</td>
                </tr>
              ))}
              {(t?.low != null || t?.mid != null || t?.high != null) && (
                <tr className="border-t-2 border-slate-500 text-white">
                  <td className="py-1.5 pr-3 font-bold">Total</td>
                  <td className="pr-3 text-right font-bold tabular-nums">{money(t.low, cur)}</td>
                  <td className="pr-3 text-right font-bold tabular-nums text-emerald-300">{money(t.mid, cur)}</td>
                  <td className="pr-3 text-right font-bold tabular-nums">{money(t.high, cur)}</td>
                  <td className="pr-3 text-xs text-slate-400" colSpan={2}>
                    {t.local_currency && t.local_mid != null ? `≈ ${money(t.local_mid, t.local_currency)} ${t.fx_note ? `(${t.fx_note})` : ""}` : ""}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
      {a.notes?.length > 0 && (
        <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-slate-300">{a.notes.map((n, i) => <li key={i}>{n}</li>)}</ul>
      )}
    </div>
  );
}
