import { NavLink, Outlet, useNavigate } from 'react-router-dom';
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
} from 'lucide-react';
import { clearSensitiveData } from '@/lib/storage';
import Logo from '@/components/brand/Logo';
import { cn } from '@/lib/utils';

const nav = [
  { to: '/admin/models', label: '模型配置', icon: Cpu },
  { to: '/admin/apis', label: '接口管理', icon: Link2 },
  { to: '/admin/knowledge', label: '知识库', icon: Library },
  { to: '/admin/templates', label: '文书模板', icon: FileCode },
  { to: '/admin/users', label: '用户管理', icon: Users },
  { to: '/admin/system', label: '系统参数', icon: Server },
  { to: '/admin/overview', label: '数据概览', icon: BarChart3, end: true },
];

export default function AdminLayout() {
  const navigate = useNavigate();

  const handleLogout = () => {
    clearSensitiveData();
    navigate('/login?portal=admin');
  };

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="flex w-[248px] shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
        <div className="border-b border-sidebar-border px-4 py-4">
          <Logo size="sm" />
          <p className="mt-2 text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            运营管理
          </p>
        </div>

        <nav className="flex-1 space-y-0.5 p-3">
          {nav.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn('nav-item', isActive && 'nav-item-active')
              }
            >
              <Icon className="h-[18px] w-[18px] opacity-70" strokeWidth={1.75} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="space-y-0.5 border-t border-sidebar-border p-3">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="nav-item w-full"
          >
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

      <main className="app-shell-main flex-1">
        <div className="relative z-[1] mx-auto max-w-5xl px-4 py-6 lg:px-10 lg:py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
