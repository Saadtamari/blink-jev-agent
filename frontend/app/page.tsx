"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Square, Swords, Zap } from "lucide-react";
import { Config, getJSON, postJSON } from "@/lib/api";
import { AgentState, useRun } from "@/lib/useRun";
import { BranchTile, Counters, FinalAnswerView, StepTimeline } from "@/components/blink";
import { ActivityFeed } from "@/components/activity-feed";
import { Landing } from "@/components/landing";
import { BorderBeam } from "@/components/ui/border-beam";
import { FlickeringGrid } from "@/components/ui/flickering-grid";
import { FlipWords } from "@/components/ui/flip-words";
import { InteractiveHoverButton } from "@/components/ui/interactive-hover-button";
import { cn } from "@/lib/utils";

const EXAMPLES = [
  { label: "Japan trip from Cairo", goal: "I want to go to Japan for 7 days in March from Cairo. How much will it cost?" },
  { label: "Paris weekend from London", goal: "How much does a 5 day trip to Paris from London cost in April?" },
  { label: "AirPods: Amazon vs eBay", goal: "Compare the price of AirPods Pro on Amazon and eBay." },
  { label: "UK visa for Egyptians", goal: "Do Egyptian citizens need a visa for the United Kingdom, and what kind?" },
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
  const [goal, setGoal] = useState(EXAMPLES[0].goal);
  const [mode, setMode] = useState<"blink" | "race">("blink");
  const [config, setConfig] = useState<Config | null>(null);
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    getJSON<Config>("/config").then(setConfig).catch(() => setError("Can't reach the Blink backend on port 8000. Start it with: python serve.py"));
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

  async function onContinue(branchId: string) {
    if (runId) await postJSON(`/runs/${runId}/branches/${branchId}/continue`);
  }

  const viewport = config?.viewport || { width: 1366, height: 900 };
  const running = !!runId && run.status === "running";
  const blink = run.agents.blink;
  const base = run.agents.baseline;

  return (
    <div className="space-y-6">
      {/* ---------- hero + command bar ---------- */}
      <section className="relative overflow-hidden rounded-2xl border border-white/10 bg-slate-950/40 shadow-[0_0_80px_-20px_rgba(56,189,248,0.25)] backdrop-blur-sm">
        <FlickeringGrid className="absolute inset-0 [mask-image:radial-gradient(600px_circle_at_top_left,white,transparent)]"
          squareSize={3} gridGap={7} color="rgb(56, 189, 248)" maxOpacity={0.18} flickerChance={0.08} />
        <div className="relative p-6 sm:p-8">
          {!runId && (
            <div className="mb-6 max-w-3xl">
              <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/5 px-3 py-1 text-xs text-emerald-300">
                <span className="relative flex size-2"><span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-60" /><span className="relative inline-flex size-2 rounded-full bg-emerald-400" /></span>
                Powered by Jev 1.14 · typed decisions with probabilities
              </div>
              <h1 className="text-3xl font-semibold tracking-tight text-white sm:text-5xl">
                The LLM plans. <span className="blink-gradient-text">Jev clicks.</span>
              </h1>
              <div className="mt-3 text-base text-slate-400 sm:text-lg">
                Ask about
                <FlipWords words={["trip costs", "flight prices", "hotel rates", "visa rules", "price comparisons"]}
                  className="px-1.5 font-medium text-slate-100" />
                and watch four tabs answer it in seconds, with a source for every number.
              </div>
            </div>
          )}

          <div className="relative rounded-xl border border-white/10 bg-slate-950/80 p-2">
            {running && <BorderBeam size={120} duration={6} colorFrom="#34d399" colorTo="#38bdf8" />}
            <div className="flex flex-col gap-2 lg:flex-row lg:items-center">
              <textarea value={goal} onChange={(e) => { setGoal(e.target.value); setError(""); }} rows={1}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); start(); } }}
                aria-label="Goal"
                className="min-h-12 max-h-40 flex-1 resize-none bg-transparent px-3 py-3 text-base text-white outline-none [field-sizing:content] placeholder:text-slate-500 sm:text-lg"
                placeholder="What should Blink find for you?" />
              <div className="flex items-center gap-2 px-1 pb-1 lg:pb-0">
                <div role="radiogroup" aria-label="Mode" className="flex rounded-full border border-white/10 bg-slate-900 p-1 text-sm">
                  {([["blink", "Blink", Zap], ["race", "Race", Swords]] as const).map(([m, label, Icon]) => (
                    <button key={m} role="radio" aria-checked={mode === m} onClick={() => setMode(m)}
                      title={m === "race" ? "Run Blink and an LLM-only agent side by side" : "Run Blink"}
                      className={cn("flex items-center gap-1.5 rounded-full px-3 py-1.5 transition",
                        mode === m ? "bg-slate-700 text-white" : "text-slate-400 hover:text-white")}>
                      <Icon className="size-3.5" />{label}
                    </button>
                  ))}
                </div>
                <InteractiveHoverButton onClick={start} disabled={starting}
                  className="border-sky-400/40 bg-slate-900 px-6 py-2.5 text-slate-100 disabled:opacity-60">
                  {starting ? "Starting" : mode === "race" ? "Race" : "Go"}
                </InteractiveHoverButton>
              </div>
            </div>
          </div>
          {error && <div className="mt-2 text-sm text-rose-300">{error}</div>}

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="text-xs text-slate-500">Try</span>
            {EXAMPLES.map((ex) => (
              <button key={ex.label} onClick={() => setGoal(ex.goal)}
                className={cn("rounded-full border px-3 py-1 text-xs transition",
                  goal === ex.goal ? "border-sky-400/40 bg-sky-400/10 text-sky-200" : "border-white/10 text-slate-300 hover:border-white/25 hover:text-white")}>
                {ex.label}
              </button>
            ))}
          </div>

          {config && (
            <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
              <span>Jev <span className={config.jev_provider === "jev" ? "text-emerald-300" : "text-amber-300"}>
                {config.jev_provider === "jev" ? config.jev_model : config.jev_provider === "mock" ? "mock (offline)" : "LLM fallback (not real Jev)"}</span></span>
              <span>Planner <span className="text-slate-300">{config.llm_planner_model}</span></span>
              <span>Tabs <span className="text-slate-300">{config.max_parallel_branches}</span></span>
              <span>Site memory <span className="text-slate-300">{config.site_memory?.entries ?? 0}</span></span>
              {!config.has_api_key && <span className="text-rose-300">No OpenRouter key in backend/.env</span>}
              {config.demo_mode && <span className="text-fuchsia-300">Demo mode: replaying a saved run</span>}
            </div>
          )}
        </div>
      </section>

      {runId && (
        <div className="flex flex-wrap items-center gap-3 text-xs">
          {run.replayOf && <span className="rounded-full bg-fuchsia-500/10 px-2.5 py-1 text-fuchsia-300">Replay of run {run.replayOf}</span>}
          {running && !run.replayOf && (
            <button onClick={() => postJSON(`/runs/${runId}/cancel`)}
              className="flex items-center gap-1.5 rounded-full border border-rose-500/40 px-3 py-1 text-rose-300 hover:bg-rose-500/10">
              <Square className="size-3" /> Stop run
            </button>
          )}
          {!running && (
            <button onClick={() => router.push("/")} className="text-slate-400 hover:text-white">← New goal</button>
          )}
        </div>
      )}

      {runId ? (
        run.mode === "race"
          ? <RaceView blink={blink} base={base} viewport={viewport} onContinue={onContinue} />
          : <AgentView agent={blink} label="Blink" accent="text-sky-300" viewport={viewport} onContinue={onContinue} withFeed />
      ) : (
        <Landing />
      )}
    </div>
  );
}

function AgentView({ agent, label, accent, viewport, onContinue, compact, withFeed }: {
  agent: AgentState; label: string; accent: string; viewport: { width: number; height: number };
  onContinue: (branchId: string) => void; compact?: boolean; withFeed?: boolean;
}) {
  const branches = agent.order.map((id) => agent.branches[id]);
  const cols = compact ? "grid-cols-[minmax(0,1fr)] sm:grid-cols-[repeat(2,minmax(0,1fr))]" : "grid-cols-[minmax(0,1fr)] md:grid-cols-[repeat(2,minmax(0,1fr))]";
  const partials = useMemo(() => branches.flatMap((b) => b.extracted.map((x) => ({ b: b.id, x }))), [branches]);
  const main = (
    <section className="min-w-0 space-y-4">
      <Counters label={label} metrics={agent.metrics} startedAt={agent.startedAt} endedAt={agent.endedAt} accent={accent} />
      {agent.plan && (
        <div className="text-xs text-slate-500">
          {agent.plan.graph.branches.length} parallel branches{" "}
          {agent.plan.graph.cached ? "(plan reused from cache)" : `planned in ${(agent.plan.plan_ms / 1000).toFixed(1)} s`}
        </div>
      )}
      {!branches.length && !agent.final && <div className="animate-pulse text-sm text-slate-400">Planning…</div>}
      <div className={`grid gap-4 ${cols}`}>
        {branches.map((b) => <BranchTile key={b.id} b={b} viewport={viewport} onContinue={onContinue} compact={compact} />)}
      </div>
      {!agent.final && partials.length > 0 && !withFeed && (
        <div className="rounded-xl border border-white/10 bg-slate-950/60 p-3 text-xs text-slate-300">
          <div className="mb-1 font-medium text-slate-400">Found so far</div>
          {partials.slice(-6).map((p, i) => (
            <div key={i} className="truncate"><span className="text-slate-500">{p.b}:</span> {JSON.stringify(p.x)}</div>
          ))}
        </div>
      )}
      <FinalAnswerView final={agent.final} title={`${label} answer`} />
      {!compact && (
        <details className="group rounded-xl border border-white/10 bg-slate-950/40 open:bg-slate-950/60">
          <summary className="cursor-pointer list-none px-4 py-3 text-sm text-slate-300 hover:text-white">
            <span className="mr-2 inline-block transition group-open:rotate-90">›</span>Step-by-step timeline
          </summary>
          <div className="grid grid-cols-[minmax(0,1fr)] gap-3 p-3 pt-0 md:grid-cols-[repeat(2,minmax(0,1fr))]">
            {branches.map((b) => <StepTimeline key={b.id} b={b} />)}
          </div>
        </details>
      )}
      {agent.errors.length > 0 && (
        <div className="text-xs text-rose-300">{agent.errors.slice(-3).map((e, i) => <div key={i}>{e}</div>)}</div>
      )}
    </section>
  );
  if (!withFeed) return main;
  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
      {main}
      <aside className="xl:sticky xl:top-20 xl:h-[calc(100vh-7rem)]"><ActivityFeed agent={agent} /></aside>
    </div>
  );
}

function RaceView({ blink, base, viewport, onContinue }: {
  blink: AgentState; base: AgentState; viewport: { width: number; height: number };
  onContinue: (branchId: string) => void;
}) {
  const blinkDone = blink.endedAt && blink.startedAt ? blink.endedAt - blink.startedAt : null;
  const baseDone = base.endedAt && base.startedAt ? base.endedAt - base.startedAt : null;
  return (
    <div className="space-y-4">
      {blinkDone && !baseDone && (
        <div className="rounded-xl border border-emerald-400/30 bg-emerald-400/5 p-4 text-center text-lg font-medium text-emerald-200">
          Blink finished in {blinkDone.toFixed(1)} s. The LLM-only agent is still working.
        </div>
      )}
      {blinkDone && baseDone && (
        <div className="rounded-xl border border-sky-400/30 bg-sky-400/5 p-4 text-center text-lg font-medium text-sky-100">
          Blink {blinkDone.toFixed(1)} s vs LLM-only {baseDone.toFixed(1)} s ·{" "}
          {baseDone >= blinkDone ? `${(baseDone / blinkDone).toFixed(1)}× faster` : `${(blinkDone / baseDone).toFixed(1)}× slower`} ·{" "}
          ${(blink.metrics?.total_cost ?? 0).toFixed(4)} vs ${(base.metrics?.total_cost ?? 0).toFixed(4)}
        </div>
      )}
      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <AgentView agent={blink} label="Blink · LLM plans, Jev clicks" accent="text-sky-300" viewport={viewport}
          onContinue={onContinue} compact />
        <AgentView agent={base} label="LLM-only agent" accent="text-amber-300" viewport={viewport}
          onContinue={onContinue} compact />
      </div>
    </div>
  );
}
