import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';
import {
  LogOut,
  Menu,
  X,
  ChevronRight,
  User,
  ChevronDown,
  Loader2,
  Sun,
  Moon,
  Shield,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useGlobalLoading } from '@/lib/loading';
import { clearSensitiveData, savePreferences } from '@/lib/storage';
import { BRAND } from '@/config/brand';
import Logo from '@/components/brand/Logo';
import {
  getNavAgents,
  getRouteLabelMap,
  getAgentByRoute,
  recordAgentVisit,
  AGENT_CATEGORIES,
  ROUTES_WITHOUT_AGENT_HEADER,
  type AgentCategory,
} from '@/config/agents';
import AgentHeader from '@/components/AgentHeader';
import IntakeResumeBar from '@/components/intake/IntakeResumeBar';
import { getChannel } from '@/lib/channels';
import { hydrateIntakeSessionFromServer } from '@/lib/intake-session';

const NAV_GROUPS: { category: AgentCategory; label: string }[] = [
  // 维权服务（主线）
  { category: 'hub', label: AGENT_CATEGORIES.service },
  { category: 'service', label: '' },
  { category: 'management', label: AGENT_CATEGORIES.management },
  { category: 'core', label: AGENT_CATEGORIES.core },
  // 专项入口（单独专区）
  { category: 'special', label: AGENT_CATEGORIES.special },
  // 其他功能（随用随走）
  { category: 'other', label: AGENT_CATEGORIES.other },
  // 账号与偏好
  { category: 'system', label: '账号' },
];

function useBreadcrumbs() {
  const location = useLocation();
  const pathMap = getRouteLabelMap();

  const parts = location.pathname.split('/').filter(Boolean);

  if (parts[0] === 'channels' && parts.length >= 2) {
    const ch = getChannel(parts[1]);
    return [
      { path: '/', label: '服务首页' },
      { path: '/channels', label: '维权专区' },
      { path: location.pathname, label: ch?.title || parts[1] },
    ];
  }

  const segments = parts.reduce<Array<{ path: string; label: string }>>((acc, _seg, idx) => {
    const path = '/' + parts.slice(0, idx + 1).join('/');
    const label = pathMap[path] || _seg;
    acc.push({ path, label });
    return acc;
  }, []);

  if (segments.length === 0 || segments[0].path !== '/') {
    return [{ path: '/', label: '服务首页' }, ...segments];
  }
  return segments.length > 0 ? segments : [{ path: '/', label: '服务首页' }];
}

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userDropdown, setUserDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { isLoading } = useGlobalLoading();

  const navAgents = useMemo(() => getNavAgents(), []);

  useEffect(() => {
    hydrateIntakeSessionFromServer().catch(() => {});
  }, []);

  const [isDark, setIsDark] = useState(() => {
    if (typeof window === 'undefined') return false;
    return document.documentElement.classList.contains('dark');
  });

  useEffect(() => {
    const stored = localStorage.getItem('theme');
    if (stored === 'dark') {
      document.documentElement.classList.add('dark');
      setIsDark(true);
    } else if (stored === 'light') {
      document.documentElement.classList.remove('dark');
      setIsDark(false);
    }
  }, []);

  const toggleDarkMode = () => {
    const nextDark = !isDark;
    setIsDark(nextDark);
    document.documentElement.classList.toggle('dark', nextDark);
    localStorage.setItem('theme', nextDark ? 'dark' : 'light');
  };

  useEffect(() => {
    savePreferences({ lastPage: location.pathname });
    const agent = navAgents.find((a) => a.route === location.pathname);
    if (agent && agent.id !== 'hub') {
      recordAgentVisit(agent.id);
    }
  }, [location.pathname, navAgents]);

  const userStr = localStorage.getItem('user');
  const user = useMemo<{ name?: string; email?: string; role?: string } | null>(() => {
    try {
      return userStr ? JSON.parse(userStr) : null;
    } catch {
      return null;
    }
  }, [userStr]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setUserDropdown(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  const handleLogout = () => {
    clearSensitiveData();
    navigate('/login');
  };

  const breadcrumbs = useBreadcrumbs();
  const currentAgent = getAgentByRoute(location.pathname);
  const showAgentHeader =
    currentAgent != null &&
    !ROUTES_WITHOUT_AGENT_HEADER.has(location.pathname) &&
    !location.pathname.startsWith('/channels/');

  const linkClass = useCallback(
    ({ isActive }: { isActive: boolean }) =>
      cn('nav-item', isActive && 'nav-item-active'),
    [],
  );

  return (
    <div className="flex h-screen overflow-hidden bg-background">
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
          <Logo size="sm" />
          <button
            type="button"
            onClick={() => setSidebarOpen(false)}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-black/5 lg:hidden"
            aria-label="关闭菜单"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4 scrollbar-thin" aria-label="主导航">
          {NAV_GROUPS.map(({ category, label }) => {
            const items = navAgents.filter((a) => a.category === category);
            if (items.length === 0) return null;
            return (
              <div key={category}>
                {label && (
                  <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground/80">
                    {label}
                  </p>
                )}
                <div className="space-y-0.5">
                  {items.map((item) => (
                    <NavLink
                      key={item.id}
                      to={item.route}
                      end={item.route === '/'}
                      className={linkClass}
                      onClick={() => setSidebarOpen(false)}
                    >
                      <item.icon className="h-[18px] w-[18px] shrink-0 opacity-70" strokeWidth={1.75} />
                      <span>{item.name}</span>
                    </NavLink>
                  ))}
                </div>
              </div>
            );
          })}
        </nav>

        <div className="border-t border-sidebar-border p-3" ref={dropdownRef}>
          <button
            type="button"
            onClick={() => setUserDropdown(!userDropdown)}
            className="flex w-full items-center gap-2.5 rounded-[var(--radius-md)] px-2 py-2 transition-colors hover:bg-black/[0.04] dark:hover:bg-white/[0.05]"
          >
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-ink text-xs font-semibold text-white">
              {user?.name?.charAt(0)?.toUpperCase() || 'U'}
            </div>
            <div className="min-w-0 flex-1 text-left">
              <p className="truncate text-sm font-medium">{user?.name || '用户'}</p>
              <p className="truncate text-[11px] text-muted-foreground">{user?.email || ''}</p>
            </div>
            <ChevronDown
              className={cn(
                'h-4 w-4 shrink-0 text-muted-foreground transition-transform',
                userDropdown && 'rotate-180',
              )}
            />
          </button>

          {userDropdown && (
            <div className="mt-1.5 overflow-hidden rounded-[var(--radius-md)] border border-border bg-card py-1 shadow-elevated">
              <button
                type="button"
                onClick={() => {
                  setUserDropdown(false);
                  navigate('/settings');
                }}
                className="flex w-full items-center gap-2.5 px-3 py-2 text-sm text-muted-foreground hover:bg-muted/60 hover:text-foreground"
              >
                <User className="h-4 w-4" />
                个人设置
              </button>
              {user?.role === 'admin' && (
                <button
                  type="button"
                  onClick={() => {
                    setUserDropdown(false);
                    navigate('/admin/models');
                  }}
                  className="flex w-full items-center gap-2.5 px-3 py-2 text-sm text-foreground hover:bg-muted/60"
                >
                  <Shield className="h-4 w-4 text-accent" />
                  管理端
                </button>
              )}
              <div className="my-1 border-t border-border/80" />
              <button
                type="button"
                onClick={() => {
                  setUserDropdown(false);
                  handleLogout();
                }}
                className="flex w-full items-center gap-2.5 px-3 py-2 text-sm text-destructive hover:bg-destructive/5"
              >
                <LogOut className="h-4 w-4" />
                退出登录
              </button>
            </div>
          )}
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header
          className="relative z-10 flex h-[52px] shrink-0 items-center gap-3 border-b border-border/80 bg-card/80 px-4 backdrop-blur-md lg:px-6"
          role="banner"
        >
          <button
            type="button"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="rounded-md p-2 text-muted-foreground hover:bg-muted/80 lg:hidden"
            aria-label="打开菜单"
          >
            <Menu className="h-5 w-5" />
          </button>

          <nav className="hidden min-w-0 items-center gap-1 text-sm lg:flex" aria-label="面包屑">
            {breadcrumbs.map((crumb, idx) => (
              <span key={crumb.path} className="flex items-center gap-1">
                {idx > 0 && <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/60" />}
                {idx === breadcrumbs.length - 1 ? (
                  <span className="font-medium text-foreground">{crumb.label}</span>
                ) : (
                  <button
                    type="button"
                    onClick={() => navigate(crumb.path)}
                    className="text-muted-foreground transition-colors hover:text-foreground"
                  >
                    {crumb.label}
                  </button>
                )}
              </span>
            ))}
          </nav>

          <span className="flex-1 truncate text-center text-sm font-medium lg:hidden">
            {breadcrumbs.length > 0 ? breadcrumbs[breadcrumbs.length - 1].label : BRAND.name}
          </span>

          <div className="ml-auto flex items-center gap-1">
            {isLoading && (
              <div role="status" className="mr-1 flex items-center gap-1.5 text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              </div>
            )}
            <button
              type="button"
              onClick={toggleDarkMode}
              className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-muted/80 hover:text-foreground"
              title={isDark ? '亮色模式' : '暗色模式'}
            >
              {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
            <button
              type="button"
              onClick={() => navigate('/settings')}
              className="hidden rounded-md p-1.5 hover:bg-muted/80 lg:block"
              title="个人设置"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-ink text-xs font-semibold text-white">
                {user?.name?.charAt(0)?.toUpperCase() || 'U'}
              </div>
            </button>
          </div>
        </header>

        <main id="main-content" className="app-shell-main" role="main">
          <div className="relative z-[1] mx-auto max-w-6xl px-4 py-6 lg:px-8 lg:py-8">
            {showAgentHeader && currentAgent && <AgentHeader agent={currentAgent} />}
            <IntakeResumeBar />
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
