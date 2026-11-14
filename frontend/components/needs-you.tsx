"use client";

import { CreditCard, ExternalLink, Hand, KeyRound } from "lucide-react";
import { Notice } from "@/lib/useRun";
import { cn } from "@/lib/utils";

const KIND = {
  verify: { icon: Hand, tone: "text-fuchsia-300", ring: "border-fuchsia-400/30 bg-fuchsia-500/5", label: "Human check" },
  login: { icon: KeyRound, tone: "text-fuchsia-300", ring: "border-fuchsia-400/30 bg-fuchsia-500/5", label: "Sign-in" },
  payment: { icon: CreditCard, tone: "text-orange-300", ring: "border-orange-400/30 bg-orange-500/5", label: "Payment" },
} as const;

/** Things only the user can do (pass a human check, sign in, pay). Stays visible for the whole run. */
export function NeedsYou({ notices, onContinue, onSkip }: {
  notices: Notice[]; onContinue?: (branch: string) => void; onSkip?: (branch: string) => void;
}) {
  if (!notices.length) return null;
  return (
    <section aria-label="Needs you" className="rounded-2xl border border-white/10 bg-slate-950/60 p-4 backdrop-blur-sm">
      <div className="mb-3 flex items-center gap-2">
        <span className="relative flex size-2"><span className="absolute inline-flex size-full animate-ping rounded-full bg-fuchsia-400 opacity-60" /><span className="relative inline-flex size-2 rounded-full bg-fuchsia-400" /></span>
        <span className="label-mono text-slate-300">Needs you · {notices.length}</span>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {notices.map((n) => {
          const k = KIND[n.kind as keyof typeof KIND] || KIND.verify;
          const Icon = k.icon;
          const done: Record<string, string> = { skipped: "Skipped · tab stopped", timeout: "No answer · tab stopped", cancelled: "Run stopped" };
          const status = n.resolved ? done[n.outcome || ""] || "Done"
            : n.blocking ? "Waiting for you" : n.kind === "payment" ? "Your decision · tab stopped" : "Optional · run continues";
          return (
            <div key={n.id} className={cn("flex gap-3 rounded-xl border p-3.5", k.ring, n.resolved && "opacity-60")}>
              <span className={cn("mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg border border-white/10 bg-slate-950/70", k.tone)}>
                <Icon className="size-4" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-white">{n.title}</span>
                  <span className={cn("label-mono rounded-full border border-white/10 px-2 py-0.5 text-[10px]",
                    n.resolved ? "text-emerald-300" : n.blocking ? "text-fuchsia-300" : "text-slate-400")}>{status}</span>
                </div>
                <p className="mt-1 text-xs leading-relaxed text-slate-400">{n.message}</p>
                <div className="mt-2 flex items-center gap-3 text-xs">
                  <span className="label-mono text-slate-500">{k.label} · {n.branch}</span>
                  {n.blocking && !n.resolved && onContinue && (
                    <button onClick={() => onContinue(n.branch)} className="font-medium text-fuchsia-300 hover:underline">I did it · Continue</button>
                  )}
                  {n.blocking && !n.resolved && onSkip && (
                    <button onClick={() => onSkip(n.branch)} className="text-slate-300 hover:underline">Skip</button>
                  )}
                  {n.url && (
                    <a href={n.url} target="_blank" rel="noreferrer"
                      className={cn("inline-flex items-center gap-1 font-medium hover:underline", k.tone)}>
                      Open site <ExternalLink className="size-3" />
                    </a>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
