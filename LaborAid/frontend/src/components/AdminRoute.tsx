import { Navigate } from 'react-router-dom';
import type { ReactNode } from 'react';
import type { User } from '@/lib/api/types';

interface AdminRouteProps {
  children: ReactNode;
}

function readUser(): User | null {
  try {
    const raw = localStorage.getItem('user');
    return raw ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
}

export default function AdminRoute({ children }: AdminRouteProps) {
  const token = localStorage.getItem('token');
  const user = readUser();

  if (!token || !user) {
    return <Navigate to="/login?portal=admin" replace />;
  }

  if (user.role !== 'admin') {
    return <Navigate to="/login?portal=admin" replace state={{ error: 'not_admin' }} />;
  }

  return <>{children}</>;
}
