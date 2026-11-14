"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getJSON, postJSON } from "@/lib/api";

type RunRow = { run_id: string; goal: string; mode: string; status: string; started: number };

export default function Runs() {
  const router = useRouter();
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    getJSON<RunRow[]>("/runs").then(setRuns).catch(() => setMsg("Can't reach the backend."));
  }, []);

  async function replay(id: string, speed: number) {
    const r = await postJSON<{ run_id: string }>(`/runs/${id}/replay`, { speed });
    router.push(`/?run=${r.run_id}`);
  }

  async function saveDemo(id: string) {
    await postJSON(`/runs/${id}/save_demo`);
    setMsg(`Saved ${id} as the demo run. Set DEMO_MODE=true in backend/.env to replay it on every Go.`);
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-white">Runs</h1>
      <p className="text-sm text-slate-400">Open a past run, replay it with its real timing (demo backup), or save it as the demo run.</p>
      {msg && <div className="text-sm text-emerald-300">{msg}</div>}
      <div className="overflow-hidden rounded-xl border border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-900 text-left text-xs uppercase text-slate-400">
            <tr><th className="px-3 py-2">When</th><th>Goal</th><th>Mode</th><th>Status</th><th className="px-3 text-right">Actions</th></tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.run_id} className="border-t border-slate-800">
                <td className="px-3 py-2 text-slate-400">{new Date(r.started * 1000).toLocaleString()}</td>
                <td className="max-w-md truncate text-slate-100">{r.goal}</td>
                <td className="text-slate-300">{r.mode}</td>
                <td className="text-slate-300">{r.status}</td>
                <td className="space-x-3 px-3 text-right text-xs">
                  <button className="text-sky-300 hover:underline" onClick={() => router.push(`/?run=${r.run_id}`)}>Open</button>
                  <button className="text-sky-300 hover:underline" onClick={() => replay(r.run_id, 1)}>Replay</button>
                  <button className="text-sky-300 hover:underline" onClick={() => replay(r.run_id, 2)}>Replay 2×</button>
                  <button className="text-fuchsia-300 hover:underline" onClick={() => saveDemo(r.run_id)}>Save as demo</button>
                </td>
              </tr>
            ))}
            {!runs.length && <tr><td colSpan={5} className="px-3 py-6 text-center text-slate-500">No runs yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
