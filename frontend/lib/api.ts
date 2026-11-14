export const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
export const WS = API.replace(/^http/, "ws");

export type Box = { x: number; y: number; w: number; h: number; confidence?: number };

export type Step = {
  id: string;
  action: string;
  target?: string | null;
  value?: string | null;
  expect?: string | null;
};

export type StepResult = {
  step_id: string;
  action: string;
  target?: string | null;
  status: string;
  used: string;
  confidence?: number | null;
  duration_ms: number;
  note?: string | null;
  data?: Record<string, unknown> | null;
};

export type CostRow = {
  category: string;
  low?: number | null;
  mid?: number | null;
  high?: number | null;
  currency: string;
  source_url?: string | null;
  note?: string | null;
};

export type FinalAnswer = {
  summary: string;
  table: CostRow[];
  totals: Record<string, unknown>;
  notes: string[];
  sources: string[];
};

export type Metrics = {
  elapsed_s: number;
  jev_calls: number;
  llm_calls: number;
  jev_cost: number;
  llm_cost: number;
  total_cost: number;
  steps: number;
  steps_by_path: Record<string, number>;
  handoffs: number;
  cache_hits: number;
};

export type BlinkEvent = {
  run_id: string;
  ts: number;
  type: string;
  agent: "blink" | "baseline";
  branch_id?: string | null;
  payload: Record<string, any>;
};

export type Config = {
  llm_planner_model: string;
  llm_fast_model: string;
  llm_vision_model: string;
  jev_provider: string;
  jev_model: string;
  max_parallel_branches: number;
  conf_act: number;
  conf_check: number;
  has_api_key: boolean;
  demo_mode: boolean;
  demo_run: string | null;
  viewport: { width: number; height: number };
  site_memory: { entries: number; hits: number };
};

export function fileUrl(path?: string | null): string | undefined {
  if (!path) return undefined;
  return `${API}/files?path=${encodeURIComponent(path)}`;
}

export async function getJSON<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

export async function postJSON<T>(path: string, body: unknown = {}): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

export function money(v: unknown, currency = "USD"): string {
  if (v === null || v === undefined || v === "" || Number.isNaN(Number(v))) return "–";
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(Number(v));
  } catch {
    return `${Math.round(Number(v)).toLocaleString()} ${currency}`;
  }
}
