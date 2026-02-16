import { useEffect, lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuthStore } from '@/stores/authStore';
import { Loader2 } from 'lucide-react';

/* Layout */
import AppLayout from '@/components/layout/AppLayout';
import ProtectedRoute from '@/components/layout/ProtectedRoute';

/* Eagerly loaded (small, critical path) */
import LoginPage from '@/pages/LoginPage';
import RegisterPage from '@/pages/RegisterPage';
import DashboardPage from '@/pages/DashboardPage';

/* Lazy loaded (heavier pages) */
const WorkflowListPage = lazy(() => import('@/pages/WorkflowListPage'));
const WorkflowEditorPage = lazy(() => import('@/pages/WorkflowEditorPage'));
const ExecutionsPage = lazy(() => import('@/pages/ExecutionsPage'));
const TriggersPage = lazy(() => import('@/pages/TriggersPage'));
const UsersPage = lazy(() => import('@/pages/UsersPage'));
const SettingsPage = lazy(() => import('@/pages/SettingsPage'));
const CredentialsPage = lazy(() => import('@/pages/CredentialsPage'));
const SchedulesPage = lazy(() => import('@/pages/SchedulesPage'));
const AuditLogPage = lazy(() => import('@/pages/AuditLogPage'));
const TemplatesPage = lazy(() => import('@/pages/TemplatesPage'));
const AgentsPage = lazy(() => import('@/pages/AgentsPage'));
const NotificationSettingsPage = lazy(() => import('@/pages/NotificationSettingsPage'));
const AdminPage = lazy(() => import('@/pages/AdminPage'));
const PluginsPage = lazy(() => import('@/pages/PluginsPage'));
const ApiDocsPage = lazy(() => import('@/pages/ApiDocsPage'));
const ExecutionDetailPage = lazy(() => import('@/pages/ExecutionDetailPage'));
const AICreatorPage = lazy(() => import('@/pages/AICreatorPage'));
const IntegrationsPage = lazy(() => import('@/pages/IntegrationsPage'));
const WorkflowFilesPage = lazy(() => import('@/pages/WorkflowFilesPage'));

import ErrorBoundary from '@/components/ErrorBoundary';
import ToastContainer from '@/components/ToastContainer';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});

/* Suspense fallback */
function PageLoader() {
  return (
    <div className="flex items-center justify-center h-64">
      <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
    </div>
  );
}

function AppRoutes() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const loadUser = useAuthStore((s) => s.loadUser);

  useEffect(() => {
    loadUser();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route path="/register" element={isAuthenticated ? <Navigate to="/" replace /> : <RegisterPage />} />

      {/* Protected routes */}
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="workflows" element={<Suspense fallback={<PageLoader />}><WorkflowListPage /></Suspense>} />
        <Route path="workflows/:id/edit" element={<Suspense fallback={<PageLoader />}><WorkflowEditorPage /></Suspense>} />
        <Route path="workflows/:id/files" element={<Suspense fallback={<PageLoader />}><WorkflowFilesPage /></Suspense>} />
        <Route path="executions" element={<Suspense fallback={<PageLoader />}><ExecutionsPage /></Suspense>} />
        <Route path="executions/:id" element={<Suspense fallback={<PageLoader />}><ExecutionDetailPage /></Suspense>} />
        <Route path="triggers" element={<Suspense fallback={<PageLoader />}><TriggersPage /></Suspense>} />
        <Route path="schedules" element={<Suspense fallback={<PageLoader />}><SchedulesPage /></Suspense>} />
        <Route path="credentials" element={<Suspense fallback={<PageLoader />}><CredentialsPage /></Suspense>} />
        <Route path="users" element={<Suspense fallback={<PageLoader />}><UsersPage /></Suspense>} />
        <Route path="settings" element={<Suspense fallback={<PageLoader />}><SettingsPage /></Suspense>} />
        <Route path="templates" element={<Suspense fallback={<PageLoader />}><TemplatesPage /></Suspense>} />
        <Route path="create" element={<Suspense fallback={<PageLoader />}><AICreatorPage /></Suspense>} />
        <Route path="agents" element={<Suspense fallback={<PageLoader />}><AgentsPage /></Suspense>} />
        <Route path="notifications" element={<Suspense fallback={<PageLoader />}><NotificationSettingsPage /></Suspense>} />
        <Route path="audit-log" element={<Suspense fallback={<PageLoader />}><AuditLogPage /></Suspense>} />
        <Route path="admin" element={<Suspense fallback={<PageLoader />}><AdminPage /></Suspense>} />
        <Route path="plugins" element={<Suspense fallback={<PageLoader />}><PluginsPage /></Suspense>} />
        <Route path="integrations" element={<Suspense fallback={<PageLoader />}><IntegrationsPage /></Suspense>} />
        <Route path="api-docs" element={<Suspense fallback={<PageLoader />}><ApiDocsPage /></Suspense>} />
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AppRoutes />
          <ToastContainer />
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
