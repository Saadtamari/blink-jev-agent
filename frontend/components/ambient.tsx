/** Page-wide atmosphere behind all content: slow aurora glows + a fading perspective grid + vignette. */
export function Ambient() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      {/* aurora glows */}
      <div className="blink-aurora absolute -left-40 -top-48 size-[42rem] rounded-full bg-emerald-500/20 blur-[120px]" />
      <div className="blink-aurora-2 absolute -right-32 -top-24 size-[36rem] rounded-full bg-sky-500/20 blur-[120px]" />
      <div className="blink-aurora absolute bottom-[-18rem] left-1/3 size-[40rem] rounded-full bg-indigo-500/10 blur-[140px]" />

      {/* grid lines, fading out from the top */}
      <div className="absolute inset-0 opacity-[0.35]
        [background-image:linear-gradient(to_right,rgb(148_163_184/0.08)_1px,transparent_1px),linear-gradient(to_bottom,rgb(148_163_184/0.08)_1px,transparent_1px)]
        [background-size:56px_56px]
        [mask-image:radial-gradient(ellipse_80%_60%_at_50%_0%,black,transparent)]" />

      {/* perspective floor grid at the bottom */}
      <div className="absolute inset-x-0 bottom-0 h-[45vh] [perspective:600px]">
        <div className="absolute inset-0 origin-bottom [transform:rotateX(62deg)]
          [background-image:linear-gradient(to_right,rgb(56_189_248/0.14)_1px,transparent_1px),linear-gradient(to_bottom,rgb(56_189_248/0.14)_1px,transparent_1px)]
          [background-size:64px_64px]
          [mask-image:linear-gradient(to_top,black,transparent)]" />
      </div>

      {/* vignette */}
      <div className="absolute inset-0 [background:radial-gradient(ellipse_at_center,transparent_40%,#070b14_100%)]" />
    </div>
  );
}
