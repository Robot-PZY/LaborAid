import { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import AdminRoute from './components/AdminRoute';
import AdminLayout from './components/AdminLayout';
import Login from './pages/Login';

// React.lazy for code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Cases = lazy(() => import('./pages/Cases'));
const DocumentGenerate = lazy(() => import('./pages/DocumentGenerate'));
const Search = lazy(() => import('./pages/Search'));
const Templates = lazy(() => import('./pages/Templates'));
const UserSettings = lazy(() => import('./pages/UserSettings'));
const AdminDashboard = lazy(() => import('./pages/admin/AdminDashboard'));
const AdminUsers = lazy(() => import('./pages/admin/AdminUsers'));
const AdminModels = lazy(() => import('./pages/admin/AdminConfig').then((m) => ({ default: () => <m.default section="models" /> })));
const AdminApis = lazy(() => import('./pages/admin/AdminConfig').then((m) => ({ default: () => <m.default section="apis" /> })));
const AdminSystem = lazy(() => import('./pages/admin/AdminConfig').then((m) => ({ default: () => <m.default section="system" /> })));
const Guidance = lazy(() => import('./pages/Guidance'));
const Records = lazy(() => import('./pages/Records'));
const ChannelLegacyRedirect = lazy(() => import('./pages/channels/ChannelLegacyRedirect'));
const Vault = lazy(() => import('./pages/Vault'));
const Evidence = lazy(() => import('./pages/Evidence'));
const Research = lazy(() => import('./pages/Research'));
const ContractReview = lazy(() => import('./pages/ContractReview'));
const EnterpriseLookup = lazy(() => import('./pages/EnterpriseLookup'));
const AdminKnowledge = lazy(() => import('./pages/admin/AdminKnowledge'));
const LimitationCalculator = lazy(() => import('./pages/tools/LimitationCalculator'));
const CompensationCalculator = lazy(() => import('./pages/tools/CompensationCalculator'));

import { BRAND } from '@/config/brand';

function PageLoader() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center py-16">
      <div className="flex flex-col items-center gap-4">
        <img
          src={BRAND.logoUrl}
          alt={BRAND.nameEn}
          className="h-11 w-11 rounded-full object-cover ring-1 ring-border/40 bg-white"
        />
        <div className="h-1 w-24 overflow-hidden rounded-full bg-muted">
          <div className="h-full w-1/2 animate-pulse rounded-full bg-accent" />
        </div>
        <p className="text-xs font-medium tracking-wide text-muted-foreground">加载中…</p>
      </div>
    </div>
  );
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/admin"
        element={
          <AdminRoute>
            <AdminLayout />
          </AdminRoute>
        }
      >
        <Route index element={<Navigate to="/admin/overview" replace />} />
        <Route path="overview" element={<Suspense fallback={<PageLoader />}><AdminDashboard /></Suspense>} />
        <Route path="models" element={<Suspense fallback={<PageLoader />}><AdminModels /></Suspense>} />
        <Route path="apis" element={<Suspense fallback={<PageLoader />}><AdminApis /></Suspense>} />
        <Route path="system" element={<Suspense fallback={<PageLoader />}><AdminSystem /></Suspense>} />
        <Route path="config" element={<Navigate to="/admin/models" replace />} />
        <Route path="users" element={<Suspense fallback={<PageLoader />}><AdminUsers /></Suspense>} />
        <Route path="knowledge" element={<Suspense fallback={<PageLoader />}><AdminKnowledge /></Suspense>} />
        <Route path="templates" element={<Suspense fallback={<PageLoader />}><Templates adminMode /></Suspense>} />
      </Route>
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Suspense fallback={<PageLoader />}><Dashboard /></Suspense>} />
        <Route path="cases" element={<Suspense fallback={<PageLoader />}><Cases /></Suspense>} />
        <Route path="documents" element={<Suspense fallback={<PageLoader />}><DocumentGenerate /></Suspense>} />
        <Route path="search" element={<Suspense fallback={<PageLoader />}><Search /></Suspense>} />
        <Route path="enterprise" element={<Suspense fallback={<PageLoader />}><EnterpriseLookup /></Suspense>} />
        <Route path="templates" element={<Suspense fallback={<PageLoader />}><Templates /></Suspense>} />
        <Route path="evidence" element={<Suspense fallback={<PageLoader />}><Evidence /></Suspense>} />
        <Route path="research" element={<Suspense fallback={<PageLoader />}><Research /></Suspense>} />
        <Route path="contracts" element={<Suspense fallback={<PageLoader />}><ContractReview /></Suspense>} />
        <Route path="tools/limitation" element={<Suspense fallback={<PageLoader />}><LimitationCalculator /></Suspense>} />
        <Route path="tools/compensation" element={<Suspense fallback={<PageLoader />}><CompensationCalculator /></Suspense>} />
        <Route path="settings" element={<Suspense fallback={<PageLoader />}><UserSettings /></Suspense>} />
        <Route path="knowledge" element={<Navigate to="/" replace />} />
        <Route path="guidance" element={<Suspense fallback={<PageLoader />}><Guidance /></Suspense>} />
        <Route path="records" element={<Suspense fallback={<PageLoader />}><Records /></Suspense>} />
        <Route path="channels" element={<Navigate to={{ pathname: '/', search: '?intake=special', hash: 'intake-desk' }} replace />} />
        <Route path="channels/:channelId" element={<Suspense fallback={<PageLoader />}><ChannelLegacyRedirect /></Suspense>} />
        <Route path="vault" element={<Suspense fallback={<PageLoader />}><Vault /></Suspense>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

export default App;
