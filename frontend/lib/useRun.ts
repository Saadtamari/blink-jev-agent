"use client";

import { useEffect, useReducer, useRef } from "react";
import { BlinkEvent, Box, FinalAnswer, Metrics, Step, StepResult, WS } from "./api";

export type StepRow = { step: Step; result?: StepResult; running: boolean };

export type BranchState = {
  id: string;
  goal: string;
  startUrl?: string;
  status: "pending" | "running" | "done" | "partial" | "failed" | "waiting_user" | "stopped";
  steps: StepRow[];
  plannedSteps: Step[];
  lastShot?: string;
  lastUrl?: string;
  lastBox?: Box & { used?: string; confidence?: number | null; shot?: string };
  perception?: { state: string; state_conf: number; locate_conf: number; target?: string };
  handoff?: { kind: string; message: string; url?: string; reason?: string };
  extracted: Record<string, unknown>[];
  startedAt?: number;
  endedAt?: number;
};

export type AgentState = {
  branches: Record<string, BranchState>;
  order: string[];
  metrics?: Metrics;
  final?: { answer: FinalAnswer | null; metrics: Metrics; error?: string };
  plan?: { graph: { branches: { id: string; goal: string; start_url: string; steps: Step[] }[] }; plan_ms: number };
  startedAt?: number;
  endedAt?: number;
  errors: string[];
  calls: { kind: "jev" | "llm"; purpose: string; ms: number; cost: number; ts: number }[];
};

export type RunState = {
  runId?: string;
  goal?: string;
  mode?: string;
  replayOf?: string;
  status: "idle" | "running" | "done";
  startedAt?: number;
  agents: Record<"blink" | "baseline", AgentState>;
  eventCount: number;
};

const emptyAgent = (): AgentState => ({ branches: {}, order: [], errors: [], calls: [] });
const initial: RunState = { status: "idle", agents: { blink: emptyAgent(), baseline: emptyAgent() }, eventCount: 0 };

function ensureBranch(a: AgentState, id: string, goal = ""): BranchState {
  if (!a.branches[id]) {
    a.branches[id] = { id, goal, status: "pending", steps: [], plannedSteps: [], extracted: [] };
    a.order = [...a.order, id];
  }
  return a.branches[id];
}

function apply(state: RunState, e: BlinkEvent): RunState {
  const s: RunState = { ...state, eventCount: state.eventCount + 1, agents: { ...state.agents } };
  const agentKey = e.agent || "blink";
  const a: AgentState = { ...s.agents[agentKey], branches: { ...s.agents[agentKey].branches } };
  s.agents[agentKey] = a;
  const p = e.payload || {};
  const bid = e.branch_id || undefined;
  const branch = bid ? { ...ensureBranch(a, bid) } : undefined;
  if (bid && branch) a.branches[bid] = branch;

  switch (e.type) {
    case "run_start":
      s.status = "running";
      s.goal = p.goal;
      s.mode = p.mode;
      s.replayOf = p.replay_of;
      s.startedAt = e.ts;
      s.agents = { blink: { ...emptyAgent(), startedAt: e.ts }, baseline: { ...emptyAgent(), startedAt: e.ts } };
      return s;
    case "plan":
      a.plan = p as AgentState["plan"];
      for (const b of p.graph.branches) {
        const br = { ...ensureBranch(a, b.id, b.goal) };
        br.plannedSteps = b.steps;
        br.startUrl = b.start_url;
        a.branches[b.id] = br;
      }
      break;
    case "branch_start":
      if (branch) {
        branch.status = "running";
        branch.goal = p.branch?.goal || branch.goal;
        branch.startedAt = e.ts;
        if (p.branch?.steps?.length) branch.plannedSteps = p.branch.steps;
      }
      break;
    case "step_start":
      if (branch) branch.steps = [...branch.steps, { step: p.step, running: true }];
      break;
    case "screenshot":
      if (branch) {
        branch.lastShot = p.path;
        branch.lastUrl = p.url;
      }
      break;
    case "action":
      if (branch && p.box) {
        // the box belongs to the screenshot it was found on: show that image with it
        branch.lastBox = { ...p.box, used: p.used, confidence: p.confidence, shot: p.screenshot };
        if (p.screenshot) branch.lastShot = p.screenshot;
      }
      break;
    case "log":
      if (branch && p.perception) branch.perception = p.perception;
      break;
    case "step_end":
      if (branch) {
        const steps = [...branch.steps];
        for (let i = steps.length - 1; i >= 0; i--) {
          if (steps[i].running) {
            steps[i] = { ...steps[i], running: false, result: p.result };
            break;
          }
        }
        branch.steps = steps;
      }
      break;
    case "handoff":
      if (branch) {
        branch.handoff = p as BranchState["handoff"];
        if (p.kind !== "payment") branch.status = "waiting_user";
      }
      break;
    case "handoff_resolved":
      if (branch) {
        branch.handoff = undefined;
        branch.status = "running";
      }
      break;
    case "partial":
      if (branch) branch.extracted = [...branch.extracted, ...(p.items || [])];
      break;
    case "branch_end":
      if (branch) {
        branch.status = p.result?.status || "done";
        branch.endedAt = e.ts;
        if (branch.handoff?.kind !== "payment") branch.handoff = undefined;
      }
      break;
    case "metrics":
      a.metrics = p as Metrics;
      break;
    case "jev_call":
    case "llm_call":
      a.calls = [...a.calls.slice(-200), { kind: e.type === "jev_call" ? "jev" : "llm", purpose: p.purpose, ms: p.ms, cost: p.cost, ts: e.ts }];
      break;
    case "final":
      a.final = p as AgentState["final"];
      a.metrics = p.metrics;
      a.endedAt = e.ts;
      break;
    case "error":
      a.errors = [...a.errors, `${p.where || ""}: ${p.error || ""}`];
      break;
    case "run_end":
      s.status = "done";
      break;
  }
  return s;
}

type Action = { kind: "reset" } | { kind: "event"; e: BlinkEvent };

function reducer(state: RunState, action: Action): RunState {
  if (action.kind === "reset") return initial;
  return apply(state, action.e);
}

export function useRun(runId?: string) {
  const [state, dispatch] = useReducer(reducer, initial);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    dispatch({ kind: "reset" });
    if (!runId) return;
    const ws = new WebSocket(`${WS}/ws/runs/${runId}`);
    wsRef.current = ws;
    ws.onmessage = (m) => {
      try {
        dispatch({ kind: "event", e: JSON.parse(m.data) });
      } catch {
        /* ignore malformed */
      }
    };
    return () => ws.close();
  }, [runId]);

  return { ...state, runId };
}
