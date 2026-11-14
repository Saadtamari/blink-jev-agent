import { cn } from "@/lib/utils";

/** Blink mark: a glowing cyan rounded frame with a solid dot in the centre (a screen and the spot Jev clicks). */
export function Logo({ className, size = 28 }: { className?: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden
      className={cn("shrink-0 drop-shadow-[0_0_6px_rgba(34,211,238,0.55)]", className)}>
      <rect x="1.5" y="1.5" width="29" height="29" rx="8.5" fill="#06121a" />
      <rect x="3" y="3" width="26" height="26" rx="7.5" stroke="#22d3ee" strokeWidth="2.6" />
      <circle cx="16" cy="16" r="5.2" fill="#22d3ee" />
    </svg>
  );
}
