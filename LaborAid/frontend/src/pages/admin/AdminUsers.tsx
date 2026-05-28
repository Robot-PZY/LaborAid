import { useEffect, useMemo, useState } from 'react';
import { Search, RefreshCw, Users } from 'lucide-react';
import { adminApi, type AdminUser } from '@/lib/api/admin';
import { useToast } from '@/lib/toast';

const ROLE_LABELS: Record<string, string> = {
  admin: '管理员',
  lawyer: '普通用户',
  assistant: '助理',
};

export default function AdminUsers() {
  const { toast } = useToast();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');

  const load = () => {
    setLoading(true);
    adminApi
      .listUsers()
      .then(setUsers)
      .catch(() => toast('加载用户列表失败', 'error'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return users;
    return users.filter(
      (u) =>
        u.name.toLowerCase().includes(q) ||
        u.email.toLowerCase().includes(q) ||
        (ROLE_LABELS[u.role] || u.role).includes(q),
    );
  }, [users, query]);

  const toggleActive = async (u: AdminUser) => {
    try {
      await adminApi.updateUser(u.id, { is_active: !u.is_active });
      toast(u.is_active ? '已禁用该账号' : '已启用该账号', 'success');
      load();
    } catch {
      toast('操作失败', 'error');
    }
  };

  const setRole = async (u: AdminUser, role: string) => {
    try {
      await adminApi.updateUser(u.id, { role });
      toast('角色已更新', 'success');
      load();
    } catch {
      toast('更新失败', 'error');
    }
  };

  const activeCount = users.filter((u) => u.is_active).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-border/80 pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-accent">运营管理</p>
          <h1 className="mt-2 font-display text-2xl font-semibold">用户管理</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            共 {users.length} 名用户，{activeCount} 名处于启用状态（不含系统内部账号）
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm hover:bg-accent disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          刷新
        </button>
      </div>

      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="搜索姓名、邮箱或角色…"
          className="w-full rounded-lg border bg-background py-2 pl-9 pr-3 text-sm"
        />
      </div>

      {loading ? (
        <p className="text-muted-foreground">加载中…</p>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-16 text-center">
          <Users className="mb-3 h-10 w-10 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">
            {query ? '没有匹配的用户' : '暂无注册用户'}
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border bg-card shadow-sm">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b bg-muted/50">
              <tr>
                <th className="px-4 py-3 font-medium">姓名</th>
                <th className="px-4 py-3 font-medium">邮箱</th>
                <th className="px-4 py-3 font-medium">角色</th>
                <th className="px-4 py-3 font-medium">状态</th>
                <th className="px-4 py-3 font-medium">注册时间</th>
                <th className="px-4 py-3 font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((u) => (
                <tr key={u.id} className="border-b last:border-0 hover:bg-muted/30">
                  <td className="px-4 py-3 font-medium">{u.name}</td>
                  <td className="px-4 py-3 text-muted-foreground">{u.email}</td>
                  <td className="px-4 py-3">
                    <select
                      value={u.role}
                      onChange={(e) => setRole(u, e.target.value)}
                      className="rounded border bg-background px-2 py-1 text-xs"
                    >
                      <option value="lawyer">普通用户</option>
                      <option value="assistant">助理</option>
                      <option value="admin">管理员</option>
                    </select>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        u.is_active
                          ? 'bg-green-100 text-green-700'
                          : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {u.is_active ? '正常' : '已禁用'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">
                    {new Date(u.created_at).toLocaleString('zh-CN')}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => toggleActive(u)}
                      className="text-xs font-medium text-foreground underline-offset-4 hover:underline"
                    >
                      {u.is_active ? '禁用' : '启用'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
