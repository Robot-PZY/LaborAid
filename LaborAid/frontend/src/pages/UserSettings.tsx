import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Shield, Loader2 } from 'lucide-react';
import { authApi } from '@/lib/api';
import type { User } from '@/lib/api/types';
import { useToast } from '@/lib/toast';
import { AxiosError } from 'axios';
import { PageHeader, Surface, Button } from '@/components/ui/primitives';

export default function UserSettings() {
  const { toast } = useToast();
  const [user, setUser] = useState<User | null>(null);
  const [name, setName] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    authApi
      .getMe()
      .then((u) => {
        setUser(u);
        setName(u.name);
        localStorage.setItem('user', JSON.stringify(u));
      })
      .catch(() => toast('加载个人信息失败', 'error'));
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    try {
      const updated = await authApi.updateMe({ name: name.trim() });
      setUser(updated);
      localStorage.setItem('user', JSON.stringify(updated));
      toast('已保存', 'success');
    } catch (err) {
      const msg = err instanceof AxiosError ? err.response?.data?.detail : '保存失败';
      toast(typeof msg === 'string' ? msg : '保存失败', 'error');
    } finally {
      setSaving(false);
    }
  };

  const isAdmin = user?.role === 'admin';

  return (
    <div className="mx-auto max-w-md space-y-8">
      <PageHeader title="个人设置" description="管理您的账号信息与偏好" />

      {isAdmin && (
        <Surface className="border-accent/20 bg-accent/5">
          <div className="flex gap-3">
            <Shield className="mt-0.5 h-5 w-5 shrink-0 text-accent" />
            <div className="text-sm">
              <p className="font-medium">平台运营</p>
              <p className="mt-1 text-muted-foreground">
                如需维护平台资料与运营设置，请前往运营后台。
              </p>
              <Link
                to="/admin/models"
                className="mt-2 inline-block text-sm font-medium text-foreground underline-offset-4 hover:underline"
              >
                进入运营后台
              </Link>
            </div>
          </div>
        </Surface>
      )}

      <form onSubmit={handleSave}>
        <Surface className="space-y-5">
          <div className="flex items-center gap-4 border-b border-border/60 pb-5">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-ink text-lg font-semibold text-white">
              {user?.name?.charAt(0)?.toUpperCase() || 'U'}
            </div>
            <div>
              <p className="font-medium">{user?.email}</p>
              <p className="text-xs text-muted-foreground">登录邮箱不可修改</p>
            </div>
          </div>

          <div>
            <label htmlFor="profile-name" className="mb-1.5 block text-xs font-medium">
              显示姓名
            </label>
            <input
              id="profile-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input-field"
              placeholder="您的姓名"
            />
          </div>

          <Button type="submit" variant="primary" className="w-full" disabled={saving}>
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            保存更改
          </Button>
        </Surface>
      </form>

    </div>
  );
}
