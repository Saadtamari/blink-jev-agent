"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Config, getJSON, postJSON } from "@/lib/api";
import { AgentState, useRun } from "@/lib/useRun";
import { BranchTile, Counters, FinalAnswerView, StepTimeline } from "@/components/ui";

const EXAMPLES = [
  "I want to go to Japan for 7 days in March from Cairo. How much will it cost?",
  "Compare the price of AirPods Pro on Amazon and eBay.",
  "How much does a 5 day trip to Paris from London cost in April?",
  "Do Egyptian citizens need a visa for the United Kingdom, and what kind?",
];

export default function Page() {
  return (
    <Suspense>
      <MissionControl />
    </Suspense>
  );
}

function MissionControl() {
  const router = useRouter();
  const params = useSearchParams();
  const runId = params.get("run") || undefined;
  const run = useRun(runId);
  const [goal, setGoal] = useState(EXAMPLES[0]);
  const [mode, setMode] = useState<"blink" | "race">("blink");
  const [config, setConfig] = useState<Config | null>(null);
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    getJSON<Config>("/config").then(setConfig).catch(() => setError("Can't reach the Blink backend at :8000. Start it with: python serve.py"));
  }, []);

  useEffect(() => {
    if (run.goal) setGoal(run.goal);
  }, [run.goal]);

  async function start() {
    if (!goal.trim()) {
      setError("Enter a goal first.");
      return;
    }
    setError("");
    setStarting(true);
    try {
      const r = await postJSON<{ run_id: string }>("/runs", { goal, mode });
      router.push(`/?run=${r.run_id}`);
    } catch (e) {
      setError(String(e));
    } finally {
      setStarting(false);
    }
  }

  async function onContinue(agent: string, branchId: string) {
    if (runId) await postJSON(`/runs/${runId}/branches/${branchId}/continue`);
  }

  const viewport = config?.viewport || { width: 1366, height: 900 };
  const isRace = run.mode === "race";
  const blink = run.agents.blink;
  const base = run.agents.baseline;

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
        <div className="flex flex-col gap-3 lg:flex-row">
          <textarea value={goal} onChange={(e) => { setGoal(e.target.value); setError(""); }} rows={2}
            className="min-h-[64px] flex-1 resize-none rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-lg text-white outline-none focus:border-sky-500"
            placeholder="What should Blink find for you?" />
          <div className="flex items-stretch gap-2">
            <div className="flex overflow-hidden rounded-xl border border-slate-700 text-sm">
              {(["blink", "race"] as const).map((m) => (
                <button key={m} onClick={() => setMode(m)}
                  className={`px-4 ${mode === m ? "bg-slate-700 text-white" : "text-slate-400 hover:text-white"}`}>
                  {m === "blink" ? "Blink" : "Race vs LLM-only"}
                </button>
              ))}
            </div>
            <button onClick={start} disabled={starting}
              className="rounded-xl bg-sky-500 px-6 text-lg font-bold text-slate-950 hover:bg-sky-400 disabled:opacity-60">
              {starting ? "Starting…" : "Go"}
            </button>
          </div>
        </div>
        {error && <div className="mt-2 text-sm text-rose-300">{error}</div>}
        <div className="mt-3 flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button key={ex} onClick={() => setGoal(ex)}
              className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:border-slate-500 hover:text-white">
              {ex.length > 60 ? ex.slice(0, 58) + "…" : ex}
            </button>
          ))}
        </div>
        {config && (
          <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-400">
            <span>Jev: <span className={config.jev_provider === "jev" ? "text-emerald-300" : "text-amber-300"}>
              {config.jev_provider === "jev" ? config.jev_model : config.jev_provider === "mock" ? "mock (offline)" : "LLM fallback (not real Jev)"}</span></span>
            <span>Planner: <span className="text-slate-200">{config.llm_planner_model}</span></span>
            <span>Vision: <span className="text-slate-200">{config.llm_vision_model}</span></span>
            <span>Parallel tabs: <span className="text-slate-200">{config.max_parallel_branches}</span></span>
            <span>Site memory: <span className="text-slate-200">{config.site_memory?.entries ?? 0} entries</span></span>
            {!config.has_api_key && <span className="text-rose-300">No OpenRouter key in backend/.env</span>}
            {config.demo_mode && <span className="text-fuchsia-300">Demo mode: replaying a saved run</span>}
          </div>
        )}
      </section>

      {run.replayOf && <div className="text-xs text-fuchsia-300">Replay of run {run.replayOf}</div>}
      {runId && run.status === "running" && !run.replayOf && (
        <button onClick={() => postJSON(`/runs/${runId}/cancel`)}
          className="rounded-lg border border-rose-500/50 px-3 py-1 text-xs text-rose-300 hover:bg-rose-950/40">
          Stop run
        </button>
      )}

      {runId && (
        isRace ? (
          <RaceView blink={blink} base={base} viewport={viewport} onContinue={onContinue} />
        ) : (
          <AgentView agent={blink} label="Blink" accent="text-sky-300" viewport={viewport} onContinue={(b) => onContinue("blink", b)} />
        )
      )}

      {!runId && (
        <div className="grid place-items-center rounded-2xl border border-dashed border-slate-800 py-24 text-center text-slate-500">
          <div>
            <div className="text-lg text-slate-300">Type a goal and press Go.</div>
            <div className="mt-1 text-sm">The LLM plans parallel branches; Jev executes every step from screenshots.</div>
          </div>
        </div>
      )}
    </div>
  );
}

function AgentView({ agent, label, accent, viewport, onContinue, compact }: {
  agent: AgentState; label: string; accent: string; viewport: { width: number; height: number };
  onContinue: (branchId: string) => void; compact?: boolean;
}) {
  const branches = agent.order.map((id) => agent.branches[id]);
  const cols = compact ? "grid-cols-[minmax(0,1fr)] sm:grid-cols-[repeat(2,minmax(0,1fr))]" : "grid-cols-[minmax(0,1fr)] md:grid-cols-[repeat(2,minmax(0,1fr))]";
  const partials = useMemo(() => branches.flatMap((b) => b.extracted.map((x) => ({ b: b.id, x }))), [branches]);
  return (
    <section className="min-w-0 space-y-4">
      <Counters label={label} metrics={agent.metrics} startedAt={agent.startedAt} endedAt={agent.endedAt} accent={accent} />
      {agent.plan && (
        <div className="text-xs text-slate-400">
          Plan: {agent.plan.graph.branches.length} parallel branches{" "}
          {agent.plan.graph.cached ? "(reused from the plan cache)" : `in ${(agent.plan.plan_ms / 1000).toFixed(1)}s`} —{" "}
          {agent.plan.graph.branches.map((b) => b.id).join(" · ")}
        </div>
      )}
      {!branches.length && !agent.final && <div className="animate-pulse text-sm text-slate-400">Planning…</div>}
      <div className={`grid gap-4 ${cols}`}>
        {branches.map((b) => <BranchTile key={b.id} b={b} viewport={viewport} onContinue={onContinue} compact={compact} />)}
      </div>
      {!agent.final && partials.length > 0 && (
        <div className="rounded-xl border border-slate-700/70 bg-slate-900/60 p-3 text-xs text-slate-300">
          <div className="mb-1 font-semibold uppercase tracking-wider text-slate-400">Found so far</div>
          {partials.slice(-8).map((p, i) => (
            <div key={i} className="truncate"><span className="text-slate-500">{p.b}:</span> {JSON.stringify(p.x)}</div>
          ))}
        </div>
      )}
      <FinalAnswerView final={agent.final} title={`${label} answer`} />
      {!compact && (
        <div className="grid grid-cols-[minmax(0,1fr)] gap-3 md:grid-cols-[repeat(2,minmax(0,1fr))]">
          {branches.map((b) => <StepTimeline key={b.id} b={b} />)}
        </div>
      )}
      {agent.errors.length > 0 && (
        <div className="text-xs text-rose-300">{agent.errors.slice(-3).map((e, i) => <div key={i}>{e}</div>)}</div>
      )}
    </section>
  );
}

function RaceView({ blink, base, viewport, onContinue }: {
  blink: AgentState; base: AgentState; viewport: { width: number; height: number };
  onContinue: (agent: string, branchId: string) => void;
}) {
  const blinkDone = blink.endedAt && blink.startedAt ? blink.endedAt - blink.startedAt : null;
  const baseDone = base.endedAt && base.startedAt ? base.endedAt - base.startedAt : null;
  return (
    <div className="space-y-4">
      {blinkDone && !baseDone && (
        <div className="rounded-xl border border-emerald-400/50 bg-emerald-950/40 p-3 text-center text-lg font-semibold text-emerald-200">
          Blink finished in {blinkDone.toFixed(1)}s — the LLM-only agent is still running
        </div>
      )}
      {blinkDone && baseDone && (
        <div className="rounded-xl border border-sky-400/50 bg-sky-950/40 p-3 text-center text-lg font-semibold text-sky-100">
          Blink {blinkDone.toFixed(1)}s vs LLM-only {baseDone.toFixed(1)}s —{" "}
          {baseDone >= blinkDone ? `${(baseDone / blinkDone).toFixed(1)}× faster` : `${(blinkDone / baseDone).toFixed(1)}× slower`},
          cost ${(blink.metrics?.total_cost ?? 0).toFixed(4)} vs ${(base.metrics?.total_cost ?? 0).toFixed(4)}
        </div>
      )}
      <div className="grid gap-6 grid-cols-[minmax(0,1fr)] xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <AgentView agent={blink} label="Blink (LLM plans, Jev clicks)" accent="text-sky-300" viewport={viewport}
          onContinue={(b) => onContinue("blink", b)} compact />
        <AgentView agent={base} label="LLM-only agent" accent="text-amber-300" viewport={viewport}
          onContinue={(b) => onContinue("baseline", b)} compact />
      </div>
    </div>
  );
}
