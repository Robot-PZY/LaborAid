import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import { Eye, EyeOff, CheckCircle, AlertCircle, Loader2, User, Shield, ArrowRight } from 'lucide-react';
import { BRAND } from '@/config/brand';
import { STORAGE_KEYS } from '@/lib/storage-keys';
import { AxiosError } from 'axios';
import { authApi } from '@/lib/api';
import { resetAuthRedirectLock } from '@/lib/api/client';
import { announceToScreenReader } from '@/lib/accessibility';
import Logo from '@/components/brand/Logo';
import { Button } from '@/components/ui/primitives';

const REMEMBER_KEY = STORAGE_KEYS.rememberEmail;

type LoginPortal = 'user' | 'admin';

interface FieldErrors {
  name?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
}

function validateEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function getPasswordStrength(pw: string): number {
  if (!pw) return 0;
  let score = 0;
  if (pw.length >= 6) score++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
  if (/\d/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  return Math.min(score, 3);
}

const STRENGTH_LABELS = ['', '弱', '中', '强'];

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();

  const initialPortal: LoginPortal =
    searchParams.get('portal') === 'admin' ? 'admin' : 'user';

  const [portal, setPortal] = useState<LoginPortal>(initialPortal);
  const [isRegister, setIsRegister] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [rememberMe, setRememberMe] = useState(false);

  const [form, setForm] = useState({
    name: '',
    email: initialPortal === 'admin' ? 'Admin' : '',
    password: '',
    confirmPassword: '',
  });

  const isAdminPortal = portal === 'admin';
  const passwordStrength = isRegister && !isAdminPortal ? getPasswordStrength(form.password) : 0;

  useEffect(() => {
    resetAuthRedirectLock();
  }, []);

  useEffect(() => {
    if (isAdminPortal) return;
    const savedEmail = localStorage.getItem(REMEMBER_KEY);
    if (savedEmail) {
      setForm((prev) => ({ ...prev, email: savedEmail }));
      setRememberMe(true);
    }
  }, [isAdminPortal]);

  const switchPortal = (next: LoginPortal) => {
    if (next === portal) return;
    setPortal(next);
    setIsRegister(false);
    setError('');
    setSuccess('');
    setFieldErrors({});
    setForm((prev) => ({
      ...prev,
      password: '',
      confirmPassword: '',
      email:
        next === 'admin'
          ? prev.email && !prev.email.includes('@')
            ? prev.email
            : 'Admin'
          : prev.email,
    }));
  };

  const clearFieldError = useCallback((field: keyof FieldErrors) => {
    setFieldErrors((prev) => {
      if (!prev[field]) return prev;
      const next = { ...prev };
      delete next[field];
      return next;
    });
  }, []);

  const validate = (): boolean => {
    const errs: FieldErrors = {};
    if (isRegister && !isAdminPortal && !form.name.trim()) errs.name = '请输入姓名';
    if (!form.email.trim()) {
      errs.email = isAdminPortal ? '请输入管理员账号' : '请输入邮箱';
    } else if (
      !isAdminPortal &&
      (isRegister || form.email.includes('@')) &&
      !validateEmail(form.email)
    ) {
      errs.email = '请输入有效的邮箱地址';
    }
    if (!form.password) errs.password = '请输入密码';
    else if (form.password.length < 6) errs.password = '密码长度不能少于6位';
    if (isRegister && !isAdminPortal) {
      if (!form.confirmPassword) errs.confirmPassword = '请再次输入密码';
      else if (form.confirmPassword !== form.password) errs.confirmPassword = '两次输入的密码不一致';
    }
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (error) setError('');
    if (success) setSuccess('');
    clearFieldError(name as keyof FieldErrors);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading || !validate()) return;

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const data =
        isRegister && !isAdminPortal
          ? await authApi.register({ email: form.email, password: form.password, name: form.name })
          : await authApi.login(form.email, form.password);

      if (isAdminPortal && data.user.role !== 'admin') {
        setError('该账号不是管理员，请切换到用户登录');
        return;
      }

      if (!isAdminPortal && rememberMe) localStorage.setItem(REMEMBER_KEY, form.email);
      else if (!isAdminPortal) localStorage.removeItem(REMEMBER_KEY);

      localStorage.setItem('token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));

      if (!isAdminPortal) {
        const { hydrateIntakeSessionFromServer } = await import('@/lib/intake-session');
        await hydrateIntakeSessionFromServer().catch(() => {});
      }

      const state = location.state as { from?: string | { pathname?: string } };
      const fromState =
        typeof state?.from === 'string' ? state.from : state?.from?.pathname;
      const fromSession = sessionStorage.getItem('auth_return_to') || undefined;
      if (fromSession) sessionStorage.removeItem('auth_return_to');
      const target = isAdminPortal ? '/admin/models' : fromState || fromSession || '/';

      setSuccess(isRegister ? '注册成功' : '登录成功');
      announceToScreenReader('登录成功');
      setTimeout(() => navigate(target, { replace: true }), 350);
    } catch (err: unknown) {
      const detail =
        err instanceof AxiosError ? err.response?.data?.detail || err.response?.data?.message : null;
      const msg =
        detail ||
        (isRegister ? '注册失败' : isAdminPortal ? '账号或密码错误' : '登录失败，请检查邮箱和密码');
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const portalFeatures = isAdminPortal
    ? ['平台运营与数据统计', '法规资料维护', '用户账号管理']
    : ['维权指引与官方服务', '文书生成与证据整理', '个人记录与材料保存'];

  return (
    <div className="flex min-h-screen">
      {/* 左侧品牌区 */}
      <aside className="login-panel-dark relative hidden w-[44%] flex-col justify-between p-10 text-white lg:flex xl:w-[42%]">
        <Logo variant="inverse" size="lg" />
        <div className="max-w-md">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-amber-300/90">
            {BRAND.subtitle}
          </p>
          <h1 className="mt-4 font-display text-3xl font-semibold leading-snug text-balance xl:text-4xl">
            {BRAND.tagline}
          </h1>
          <p className="mt-4 text-sm leading-relaxed text-white/65">{BRAND.description}</p>
        </div>
        <p className="text-xs text-white/40">© {new Date().getFullYear()} {BRAND.name}</p>
        <div
          className="pointer-events-none absolute -right-20 top-1/3 h-64 w-64 rounded-full bg-amber-400/10 blur-3xl"
          aria-hidden
        />
      </aside>

      {/* 右侧表单 */}
      <div className="flex flex-1 flex-col justify-center px-5 py-10 sm:px-10 lg:px-14">
        <div className="mx-auto w-full max-w-[400px]">
          <div className="mb-8 lg:hidden">
            <Logo size="md" />
          </div>

          <div className="mb-6 inline-flex rounded-[var(--radius-md)] border border-border bg-muted/50 p-1">
            <button
              type="button"
              onClick={() => switchPortal('user')}
              className={`flex items-center gap-2 rounded-[calc(var(--radius-md)-2px)] px-4 py-2 text-sm font-medium transition-all ${
                portal === 'user' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground'
              }`}
            >
              <User className="h-4 w-4" />
              用户
            </button>
            <button
              type="button"
              onClick={() => switchPortal('admin')}
              className={`flex items-center gap-2 rounded-[calc(var(--radius-md)-2px)] px-4 py-2 text-sm font-medium transition-all ${
                portal === 'admin' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground'
              }`}
            >
              <Shield className="h-4 w-4" />
              管理
            </button>
          </div>

          <h2 className="font-display text-2xl font-semibold tracking-tight">
            {isAdminPortal ? '管理端登录' : isRegister ? '注册账户' : '欢迎回来'}
          </h2>
          <p className="mt-1.5 text-sm text-muted-foreground">
            {isAdminPortal ? '平台运营管理' : '登录后使用维权服务与法律工具'}
          </p>

          <ul className="mt-5 space-y-2">
            {portalFeatures.map((f) => (
              <li key={f} className="flex items-center gap-2 text-xs text-muted-foreground">
                <span className="h-1 w-1 shrink-0 rounded-full bg-accent" />
                {f}
              </li>
            ))}
          </ul>

          {success && (
            <div className="mt-5 flex items-center gap-2 rounded-[var(--radius-md)] border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-sm text-emerald-800">
              <CheckCircle className="h-4 w-4" />
              {success}，正在跳转…
            </div>
          )}

          {error && (
            <div className="mt-5 flex items-center gap-2 rounded-[var(--radius-md)] border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700" role="alert">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}

          {isAdminPortal && import.meta.env.DEV && (
            <p className="mt-4 rounded-[var(--radius-md)] border border-dashed border-border bg-muted/40 px-3 py-2 text-[11px] text-muted-foreground">
              管理员账号 <strong className="text-foreground">Admin</strong> 或{' '}
              <strong className="text-foreground">admin@laboraid.local</strong>，密码{' '}
              <strong className="text-foreground">123456</strong>
            </p>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4" noValidate>
            {isRegister && !isAdminPortal && (
              <div>
                <label htmlFor="login-name" className="mb-1.5 block text-xs font-medium text-foreground">
                  姓名
                </label>
                <input
                  id="login-name"
                  name="name"
                  className={`input-field ${fieldErrors.name ? 'border-red-300' : ''}`}
                  value={form.name}
                  onChange={handleChange}
                  placeholder="您的姓名"
                  autoComplete="name"
                />
                {fieldErrors.name && <p className="mt-1 text-xs text-red-600">{fieldErrors.name}</p>}
              </div>
            )}

            <div>
              <label htmlFor="login-email" className="mb-1.5 block text-xs font-medium text-foreground">
                {isAdminPortal ? '管理员账号' : '邮箱'}
              </label>
              <input
                id="login-email"
                name="email"
                type={isAdminPortal ? 'text' : 'email'}
                className={`input-field ${fieldErrors.email ? 'border-red-300' : ''}`}
                value={form.email}
                onChange={handleChange}
                placeholder={isAdminPortal ? 'Admin（区分大小写）' : 'name@example.com'}
                autoComplete="username"
              />
              {fieldErrors.email && <p className="mt-1 text-xs text-red-600">{fieldErrors.email}</p>}
            </div>

            <div>
              <label htmlFor="login-password" className="mb-1.5 block text-xs font-medium text-foreground">
                密码
              </label>
              <div className="relative">
                <input
                  id="login-password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  className={`input-field pr-10 ${fieldErrors.password ? 'border-red-300' : ''}`}
                  value={form.password}
                  onChange={handleChange}
                  placeholder="至少 6 位"
                  autoComplete={isRegister ? 'new-password' : 'current-password'}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  aria-label={showPassword ? '隐藏密码' : '显示密码'}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {fieldErrors.password && <p className="mt-1 text-xs text-red-600">{fieldErrors.password}</p>}
              {isRegister && !isAdminPortal && form.password && !fieldErrors.password && (
                <p className="mt-1 text-xs text-muted-foreground">
                  强度：{STRENGTH_LABELS[passwordStrength] || '弱'}
                </p>
              )}
            </div>

            {isRegister && !isAdminPortal && (
              <div>
                <label htmlFor="login-confirm" className="mb-1.5 block text-xs font-medium text-foreground">
                  确认密码
                </label>
                <input
                  id="login-confirm"
                  name="confirmPassword"
                  type="password"
                  className={`input-field ${fieldErrors.confirmPassword ? 'border-red-300' : ''}`}
                  value={form.confirmPassword}
                  onChange={handleChange}
                />
                {fieldErrors.confirmPassword && (
                  <p className="mt-1 text-xs text-red-600">{fieldErrors.confirmPassword}</p>
                )}
              </div>
            )}

            {!isRegister && !isAdminPortal && (
              <label className="flex cursor-pointer items-center gap-2 text-sm text-muted-foreground">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="rounded border-input text-accent focus:ring-accent"
                />
                记住邮箱
              </label>
            )}

            <Button
              type="submit"
              variant={isAdminPortal ? 'primary' : 'secondary'}
              className="w-full"
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  处理中…
                </>
              ) : (
                <>
                  {isRegister ? '注册' : isAdminPortal ? '进入管理端' : '进入平台'}
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </Button>
          </form>

          {!isAdminPortal && (
            <p className="mt-6 text-center text-sm text-muted-foreground">
              {isRegister ? '已有账户？' : '还没有账户？'}
              <button
                type="button"
                onClick={() => {
                  setIsRegister(!isRegister);
                  setError('');
                  setFieldErrors({});
                }}
                className="ml-1 font-medium text-foreground underline-offset-4 hover:underline"
              >
                {isRegister ? '去登录' : '注册'}
              </button>
            </p>
          )}

          {isAdminPortal && (
            <p className="mt-6 text-center text-xs text-muted-foreground">
              <button type="button" onClick={() => switchPortal('user')} className="hover:underline">
                返回用户登录
              </button>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
