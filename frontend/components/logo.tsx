import { cn } from "@/lib/utils";

/** Blink mark: a glowing cyan frame with an inner "target" square (a screen and the spot Jev clicks). */
export function Logo({ className, size = 28 }: { className?: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden
      className={cn("shrink-0 drop-shadow-[0_0_6px_rgba(34,211,238,0.55)]", className)}>
      <rect x="1.5" y="1.5" width="29" height="29" rx="8.5" fill="#06121a" />
      <rect x="2.75" y="2.75" width="26.5" height="26.5" rx="7.5" stroke="#22d3ee" strokeWidth="2.5" />
      <rect x="10.25" y="10.25" width="11.5" height="11.5" rx="3" stroke="#22d3ee" strokeWidth="2.5" />
    </svg>
  );
}
