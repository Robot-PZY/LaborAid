/**
 * 首页顶部装饰横幅 — 仅视觉呈现，不承担功能说明。
 */
export default function DashboardHeroBanner({ greeting }: { greeting: string }) {
  return (
    <section
      className="relative overflow-hidden rounded-2xl border border-border/50 shadow-card"
      aria-hidden={false}
    >
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-rose-400/25 via-amber-300/20 to-sky-400/30 dark:from-rose-600/20 dark:via-amber-500/15 dark:to-sky-600/25" />
      <div className="pointer-events-none absolute -left-16 top-8 h-48 w-48 rounded-full bg-accent/30 blur-3xl dashboard-blob" />
      <div className="pointer-events-none absolute -right-10 -top-10 h-56 w-56 rounded-full bg-violet-400/25 blur-3xl dashboard-blob-delayed" />
      <div className="pointer-events-none absolute bottom-0 left-1/3 h-40 w-72 rounded-full bg-amber-400/20 blur-3xl" />

      {/* 装饰几何 */}
      <svg
        className="pointer-events-none absolute right-0 top-0 h-full w-[55%] max-w-xl opacity-90"
        viewBox="0 0 400 200"
        preserveAspectRatio="xMaxYMid slice"
        aria-hidden
      >
        <defs>
          <linearGradient id="dash-arc-a" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="hsl(var(--accent))" stopOpacity="0.55" />
            <stop offset="100%" stopColor="hsl(262 70% 58%)" stopOpacity="0.15" />
          </linearGradient>
          <linearGradient id="dash-arc-b" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="hsl(32 95% 55%)" stopOpacity="0.45" />
            <stop offset="100%" stopColor="hsl(199 80% 52%)" stopOpacity="0.2" />
          </linearGradient>
        </defs>
        <circle cx="320" cy="100" r="72" fill="url(#dash-arc-a)" opacity="0.35" />
        <circle cx="280" cy="60" r="40" fill="url(#dash-arc-b)" opacity="0.4" />
        <circle cx="350" cy="140" r="28" fill="hsl(var(--accent))" opacity="0.25" />
        <path
          d="M40 160 Q120 40 200 100 T360 80"
          fill="none"
          stroke="hsl(var(--accent))"
          strokeWidth="2"
          strokeOpacity="0.35"
          strokeLinecap="round"
        />
        <path
          d="M60 180 Q180 120 260 150 T380 120"
          fill="none"
          stroke="hsl(32 90% 55%)"
          strokeWidth="1.5"
          strokeOpacity="0.4"
          strokeLinecap="round"
        />
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <circle
            key={i}
            cx={120 + i * 42}
            cy={90 + (i % 3) * 22}
            r={4 + (i % 2) * 2}
            fill="hsl(var(--foreground))"
            opacity={0.08 + i * 0.04}
          />
        ))}
      </svg>

      <div className="relative z-10 px-6 py-10 sm:px-10 sm:py-12">
        <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-accent/80">
          LaborAid
        </p>
        <h1 className="mt-3 font-display text-2xl font-semibold tracking-tight text-foreground sm:text-4xl">
          {greeting}
        </h1>
        <p className="mt-2 max-w-md text-sm text-muted-foreground/90">
          劳权智助 · 劳动者维权服务
        </p>
      </div>
    </section>
  );
}
