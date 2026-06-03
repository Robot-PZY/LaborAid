import { Link } from 'react-router-dom';
import { Compass, Archive, History } from 'lucide-react';

const LINKS = [
  { to: '/guidance', label: '办事资源', icon: Compass },
  { to: '/vault', label: '材料库', icon: Archive },
  { to: '/records', label: '我的记录', icon: History },
] as const;

/** 服务层页面底部快捷导航 */
export default function ServiceStrip() {
  return (
    <nav
      className="flex flex-wrap gap-2 border-t border-border/60 pt-8"
      aria-label="服务快捷导航"
    >
      <span className="w-full text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        继续浏览
      </span>
      {LINKS.map(({ to, label, icon: Icon }) => (
        <Link
          key={to}
          to={to}
          className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-foreground/20 hover:text-foreground"
        >
          <Icon className="h-3.5 w-3.5" strokeWidth={1.75} />
          {label}
        </Link>
      ))}
    </nav>
  );
}
