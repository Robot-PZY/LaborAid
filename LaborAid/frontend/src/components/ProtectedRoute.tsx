import { Navigate, useLocation } from 'react-router-dom';
import type { ReactNode } from 'react';

interface ProtectedRouteProps {
  children: ReactNode;
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const location = useLocation();
  const token = localStorage.getItem('token');

  // Validate token exists and is not empty/invalid format
  if (!token || token.trim().length === 0) {
    // Preserve the attempted URL for redirect after login
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  // Verify user data exists alongside token
  const userStr = localStorage.getItem('user');
  if (!userStr) {
    // Token exists but no user data — clear and redirect
    localStorage.removeItem('token');
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  try {
    JSON.parse(userStr);
  } catch {
    // Corrupted user data — clear and redirect
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  return <>{children}</>;
}
