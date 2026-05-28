import type { ReactNode, ButtonHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

/** 页面顶栏标题区 */
export function PageHeader({
  eyebrow,
  title,
  description,
  action,
  className,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <header
      className={cn(
        'mb-8 flex flex-col gap-4 border-b border-border/80 pb-6 sm:flex-row sm:items-end sm:justify-between',
        className,
      )}
    >
      <div className="max-w-2xl">
        {eyebrow && (
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-accent">
            {eyebrow}
          </p>
        )}
        <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
          {title}
        </h1>
        {description && (
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </header>
  );
}

/** 区块标题 */
export function SectionTitle({
  title,
  description,
  className,
}: {
  title: string;
  description?: string;
  className?: string;
}) {
  return (
    <div className={cn('mb-4', className)}>
      <h2 className="font-display text-lg font-semibold text-foreground">{title}</h2>
      {description && (
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      )}
    </div>
  );
}

/** 纸面卡片 */
export function Surface({
  children,
  className,
  padding = 'md',
  hover,
}: {
  children: ReactNode;
  className?: string;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  hover?: boolean;
}) {
  const pad = { none: '', sm: 'p-4', md: 'p-5', lg: 'p-6 sm:p-8' }[padding];
  return (
    <div
      className={cn(
        'rounded-[var(--radius-lg)] border border-border/70 bg-card shadow-[var(--shadow-card)]',
        pad,
        hover && 'transition-shadow duration-200 hover:shadow-[var(--shadow-card-hover)]',
        className,
      )}
    >
      {children}
    </div>
  );
}

const btnBase =
  'inline-flex items-center justify-center gap-2 rounded-[var(--radius-md)] text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50';

export function Button({
  variant = 'primary',
  size = 'md',
  className,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
}) {
  const sizes = { sm: 'h-8 px-3 text-xs', md: 'h-10 px-4', lg: 'h-11 px-5' };
  const variants = {
    primary: 'bg-ink text-white hover:bg-ink/90 shadow-sm',
    secondary: 'bg-accent text-accent-foreground hover:bg-accent/90 shadow-sm',
    outline: 'border border-border bg-transparent hover:bg-muted/80',
    ghost: 'hover:bg-muted/80 text-foreground',
  };
  return (
    <button
      type="button"
      className={cn(btnBase, sizes[size], variants[variant], className)}
      {...props}
    >
      {children}
    </button>
  );
}

export function Badge({
  children,
  tone = 'neutral',
  className,
}: {
  children: ReactNode;
  tone?: 'neutral' | 'accent' | 'success' | 'warning';
  className?: string;
}) {
  const tones = {
    neutral: 'bg-muted text-foreground/75 border border-border/60',
    accent: 'bg-accent-soft text-accent-soft-fg border border-accent/35 font-semibold',
    success: 'bg-emerald-100 text-emerald-900 border border-emerald-200/80 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800/50',
    warning: 'bg-amber-100 text-amber-950 border border-amber-200/80 dark:bg-amber-950/50 dark:text-amber-200 dark:border-amber-800/50',
  };
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium',
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
