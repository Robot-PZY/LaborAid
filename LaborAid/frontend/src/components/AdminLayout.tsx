import { useEffect, useState } from 'react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import {
  BarChart3,
  Cpu,
  Link2,
  Server,
  Users,
  LogOut,
  ArrowLeft,
  Library,
  FileCode,
  Menu,
  X,
  Sun,
  Moon,
} from 'lucide-react';
import { clearSensitiveData } from '@/lib/storage';
import { useTheme } from '@/lib/use-theme';
import Logo from '@/components/brand/Logo';
import { cn } from '@/lib/utils';

type NavItem = { to: string; label: string; icon: LucideIcon; end?: boolean };

const NAV_GROUPS: { label: string; items: NavItem[] }[] = [
  {
    label: '运营监控',
    items: [
      { to: '/admin/overview', label: '数据概览', icon: BarChart3, end: true },
      { to: '/admin/users', label: '用户管理', icon: Users },
    ],
  },
  {
    label: '平台配置',
    items: [
      { to: '/admin/models', label: '模型配置', icon: Cpu },
      { to: '/admin/apis', label: '接口管理', icon: Link2 },
      { to: '/admin/system', label: '系统参数', icon: Server },
    ],
  },
  {
    label: '内容管理',
    items: [
      { to: '/admin/knowledge', label: '知识库', icon: Library },
      { to: '/admin/templates', label: '文书模板', icon: FileCode },
    ],
  },
];

function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4 scrollbar-thin" aria-label="管理端导航">
      {NAV_GROUPS.map((group) => (
        <div key={group.label}>
          <p className="mb-1.5 px-2.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
            {group.label}
          </p>
          <div className="space-y-0.5">
            {group.items.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                onClick={onNavigate}
                className={({ isActive }) => cn('nav-item', isActive && 'nav-item-active')}
              >
                <Icon className="h-[18px] w-[18px] opacity-70" strokeWidth={1.75} />
                {label}
              </NavLink>
            ))}
          </div>
        </div>
      ))}
    </nav>
  );
}

export default function AdminLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { isDark, toggle: toggleDarkMode } = useTheme();

  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  const handleLogout = () => {
    clearSensitiveData();
    navigate('/login?portal=admin');
  };

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <a
        href="#admin-main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-card focus:px-3 focus:py-2 focus:text-sm focus:shadow"
      >
        跳到主内容
      </a>

      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-ink/40 backdrop-blur-[2px] lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden
        />
      )}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex w-[248px] flex-col border-r border-sidebar-border bg-sidebar transition-transform duration-300 ease-out lg:static lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-[60px] items-center justify-between border-b border-sidebar-border px-4">
          <div>
            <Logo size="sm" />
            <p className="mt-0.5 text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              运营管理
            </p>
          </div>
          <button
            type="button"
            onClick={() => setSidebarOpen(false)}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-black/5 dark:hover:bg-white/5 lg:hidden"
            aria-label="关闭菜单"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <SidebarNav onNavigate={() => setSidebarOpen(false)} />

        <div className="space-y-0.5 border-t border-sidebar-border p-3">
          <button type="button" onClick={() => navigate('/')} className="nav-item w-full">
            <ArrowLeft className="h-[18px] w-[18px] opacity-70" />
            预览用户端
          </button>
          <button
            type="button"
            onClick={handleLogout}
            className="nav-item w-full text-destructive hover:bg-destructive/5"
          >
            <LogOut className="h-[18px] w-[18px]" />
            退出管理端
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-border/70 bg-card/80 px-4 backdrop-blur-sm lg:hidden">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className="rounded-md p-2 text-muted-foreground hover:bg-muted"
            aria-label="打开菜单"
          >
            <Menu className="h-5 w-5" />
          </button>
          <span className="text-sm font-medium text-muted-foreground">管理端</span>
          <button
            type="button"
            onClick={toggleDarkMode}
            className="rounded-md p-2 text-muted-foreground hover:bg-muted"
            aria-label={isDark ? '切换浅色模式' : '切换深色模式'}
          >
            {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </button>
        </header>

        <div className="hidden lg:flex shrink-0 items-center justify-end border-b border-border/70 bg-card/50 px-6 py-2">
          <button
            type="button"
            onClick={toggleDarkMode}
            className="inline-flex items-center gap-2 rounded-md px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted"
            aria-label={isDark ? '切换浅色模式' : '切换深色模式'}
          >
            {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            {isDark ? '浅色模式' : '深色模式'}
          </button>
        </div>

        <main id="admin-main" className="app-shell-main flex-1 overflow-y-auto" role="main">
          <div className="relative z-[1] mx-auto max-w-7xl px-4 py-6 lg:px-10 lg:py-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
