import { useId, useMemo } from 'react';

export type ChartSegment = {
  label: string;
  value: number;
  color: string;
};

export const CHART_COLORS = {
  cases: 'hsl(222 55% 42%)',
  documents: 'hsl(32 90% 48%)',
  evidence: 'hsl(152 45% 40%)',
  research: 'hsl(262 55% 52%)',
  users: 'hsl(199 70% 45%)',
  inactive: 'hsl(220 10% 78%)',
} as const;

function polar(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function arcPath(cx: number, cy: number, r: number, start: number, end: number) {
  const s = polar(cx, cy, r, end);
  const e = polar(cx, cy, r, start);
  const large = end - start > 180 ? 1 : 0;
  return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 0 ${e.x} ${e.y}`;
}

export function DonutChart({
  segments,
  size = 160,
  stroke = 22,
  centerLabel,
  centerSub,
}: {
  segments: ChartSegment[];
  size?: number;
  stroke?: number;
  centerLabel?: string;
  centerSub?: string;
}) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  const cx = size / 2;
  const cy = size / 2;
  const r = (size - stroke) / 2;

  let angle = 0;
  const arcs = segments
    .filter((s) => s.value > 0)
    .map((seg) => {
      const sweep = (seg.value / total) * 360;
      const start = angle;
      const end = angle + sweep;
      angle = end;
      return { ...seg, path: arcPath(cx, cy, r, start, Math.max(start + 0.5, end - 0.5)) };
    });

  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start">
      <div className="relative shrink-0" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="overflow-visible" aria-hidden>
          <circle
            cx={cx}
            cy={cy}
            r={r}
            fill="none"
            stroke="hsl(var(--muted))"
            strokeWidth={stroke}
          />
          {arcs.map((a) => (
            <path
              key={a.label}
              d={a.path}
              fill="none"
              stroke={a.color}
              strokeWidth={stroke}
              strokeLinecap="round"
            />
          ))}
        </svg>
        {(centerLabel || centerSub) && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
            {centerLabel && (
              <span className="font-display text-xl font-semibold tabular-nums">{centerLabel}</span>
            )}
            {centerSub && <span className="text-[10px] text-muted-foreground">{centerSub}</span>}
          </div>
        )}
      </div>
      <ul className="flex flex-1 flex-wrap gap-x-4 gap-y-2 text-sm">
        {segments.map((s) => (
          <li key={s.label} className="flex items-center gap-2">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: s.color }}
            />
            <span className="text-muted-foreground">{s.label}</span>
            <span className="font-medium tabular-nums">{s.value}</span>
            <span className="text-xs text-muted-foreground">
              ({Math.round((s.value / total) * 100)}%)
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export type TrendRow = {
  label: string;
  cases: number;
  documents: number;
  evidence: number;
  research: number;
};

const TREND_KEYS = ['cases', 'documents', 'evidence', 'research'] as const;

export function StackedBarChart({
  rows,
  height = 200,
  colors = CHART_COLORS,
}: {
  rows: TrendRow[];
  height?: number;
  colors?: typeof CHART_COLORS;
}) {
  const maxTotal = useMemo(
    () =>
      Math.max(
        1,
        ...rows.map((r) => r.cases + r.documents + r.evidence + r.research),
      ),
    [rows],
  );

  const barW = rows.length > 0 ? Math.min(48, Math.max(12, 320 / rows.length)) : 24;
  const gap = 8;
  const chartW = rows.length * (barW + gap);

  return (
    <div className="w-full overflow-x-auto">
      <svg
        width={Math.max(chartW, 280)}
        height={height + 28}
        className="mx-auto"
        role="img"
        aria-label="近七日堆叠柱状图"
      >
        {rows.map((row, i) => {
          const total = row.cases + row.documents + row.evidence + row.research;
          const x = i * (barW + gap) + gap / 2;
          const stacks = [
            { v: row.cases, c: colors.cases },
            { v: row.documents, c: colors.documents },
            { v: row.evidence, c: colors.evidence },
            { v: row.research, c: colors.research },
          ];
          let stacked = 0;
          return (
            <g key={row.label}>
              {stacks.map((s, si) => {
                if (s.v <= 0) return null;
                const segH = (s.v / maxTotal) * height;
                const ySeg = height - ((stacked + s.v) / maxTotal) * height;
                stacked += s.v;
                return (
                  <rect
                    key={si}
                    x={x}
                    y={ySeg}
                    width={barW}
                    height={Math.max(segH, 2)}
                    fill={s.c}
                    opacity={0.92}
                    rx={2}
                  />
                );
              })}
              <text
                x={x + barW / 2}
                y={height + 18}
                textAnchor="middle"
                className="fill-muted-foreground text-[10px]"
              >
                {row.label}
              </text>
              {total > 0 && (
                <text
                  x={x + barW / 2}
                  y={height - (total / maxTotal) * height - 4}
                  textAnchor="middle"
                  className="fill-foreground text-[9px] font-medium"
                >
                  {total}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      <div className="mt-3 flex flex-wrap justify-center gap-3 text-xs">
        {[
          { label: '案件', color: colors.cases },
          { label: '文书', color: colors.documents },
          { label: '证据', color: colors.evidence },
          { label: '研究', color: colors.research },
        ].map((l) => (
          <span key={l.label} className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-sm" style={{ backgroundColor: l.color }} />
            {l.label}
          </span>
        ))}
      </div>
    </div>
  );
}

export function Sparkline({
  values,
  color = CHART_COLORS.cases,
  height = 48,
  width = 160,
}: {
  values: number[];
  color?: string;
  height?: number;
  width?: number;
}) {
  const gradId = useId();
  const path = useMemo(() => {
    if (values.length < 2) return '';
    const max = Math.max(1, ...values);
    const step = width / (values.length - 1);
    const pts = values.map((v, i) => {
      const x = i * step;
      const y = height - (v / max) * (height - 8) - 4;
      return `${x},${y}`;
    });
    return `M ${pts.join(' L ')}`;
  }, [values, height, width]);

  const area = path ? `${path} L ${width},${height} L 0,${height} Z` : '';

  if (values.every((v) => v === 0)) {
    return (
      <svg width={width} height={height} className="opacity-40">
        <line x1={0} y1={height / 2} x2={width} y2={height / 2} stroke="hsl(var(--muted))" strokeDasharray="4 4" />
      </svg>
    );
  }

  return (
    <svg width={width} height={height} aria-hidden>
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.35} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      {area && <path d={area} fill={`url(#${gradId})`} />}
      {path && (
        <path d={path} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
      )}
    </svg>
  );
}

export function ProgressRing({
  value,
  max = 100,
  size = 72,
  stroke = 7,
  color = CHART_COLORS.cases,
  label,
}: {
  value: number;
  max?: number;
  size?: number;
  stroke?: number;
  color?: string;
  label?: string;
}) {
  const pct = Math.min(100, Math.round((value / Math.max(max, 1)) * 100));
  const cx = size / 2;
  const cy = size / 2;
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;

  return (
    <div className="relative inline-flex flex-col items-center" style={{ width: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="hsl(var(--muted))"
          strokeWidth={stroke}
        />
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-700"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center font-display text-sm font-semibold tabular-nums">
        {pct}%
      </span>
      {label && <span className="mt-1 text-center text-[10px] text-muted-foreground">{label}</span>}
    </div>
  );
}

export function MiniBarCompare({
  items,
}: {
  items: { label: string; value: number; color: string }[];
}) {
  const max = Math.max(1, ...items.map((i) => i.value));
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={item.label}>
          <div className="mb-1 flex justify-between text-xs">
            <span className="text-muted-foreground">{item.label}</span>
            <span className="font-medium tabular-nums">{item.value}</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${Math.max(item.value > 0 ? 8 : 0, (item.value / max) * 100)}%`,
                backgroundColor: item.color,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
