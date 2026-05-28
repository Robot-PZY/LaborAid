export default function PageSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-28 rounded-[var(--radius-lg)] bg-muted" />
      <div className="grid gap-3 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-20 rounded-[var(--radius-md)] bg-muted" />
        ))}
      </div>
      <div className="space-y-2">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="h-16 rounded-[var(--radius-md)] bg-muted" />
        ))}
      </div>
    </div>
  );
}
