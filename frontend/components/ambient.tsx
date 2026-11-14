/** Page-wide atmosphere: a dot matrix, fine vertical lines and one soft glow. Monochrome, works in both themes. */
export function Ambient() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      {/* one soft glow behind the hero */}
      <div className="blink-aurora absolute -top-64 left-1/2 size-[46rem] -translate-x-1/2 rounded-full bg-emerald-500/10 blur-[140px]" />

      {/* dot matrix, fading out from the top right */}
      <div className="absolute inset-0
        [background-image:radial-gradient(var(--dot)_1px,transparent_1.2px)]
        [background-size:18px_18px]
        [mask-image:radial-gradient(ellipse_70%_55%_at_85%_10%,black,transparent)]" />

      {/* fine vertical lines band at the bottom */}
      <div className="absolute inset-x-0 bottom-0 h-[38vh]
        [background-image:linear-gradient(to_right,var(--grid-line)_1px,transparent_1px)]
        [background-size:9px_100%]
        [mask-image:linear-gradient(to_top,black,transparent)]" />

      {/* page frame lines, like a document grid */}
      <div className="absolute inset-y-0 left-1/2 w-full max-w-[1600px] -translate-x-1/2 border-x border-[var(--grid-line)]" />
    </div>
  );
}
