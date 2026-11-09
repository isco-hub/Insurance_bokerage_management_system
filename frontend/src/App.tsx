import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ResourcePage } from './components/ResourcePage';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { resources } from './config/resources';

const AccountPage = lazy(() => import('./pages/AccountPage'));
const ApprovalReviewPage = lazy(() => import('./pages/ApprovalReviewPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const LandingPage = lazy(() => import('./pages/LandingPage'));
const LoginPage = lazy(() => import('./pages/LoginPage'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'));
const RecordDetailPage = lazy(() => import('./pages/RecordDetailPage'));
const ReportsPage = lazy(() => import('./pages/ReportsPage'));
const SearchPage = lazy(() => import('./pages/SearchPage'));

function PageFallback() {
  return (
    <div className="page">
      <div className="content-card report-loading">
        <span className="spinner spinner-dark" />
        <p>Loading…</p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Suspense fallback={<PageFallback />}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="account" element={<AccountPage />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="approvals/:id" element={<ApprovalReviewPage />} />
            <Route path="search" element={<SearchPage />} />
            {resources
              .filter((resource) => resource.detailEntityType)
              .map((resource) => (
                <Route
                  key={`${resource.key}-detail`}
                  path={`${resource.path.replace(/^\//, '')}/:id`}
                  element={<RecordDetailPage config={resource} />}
                />
              ))}
            {resources.map((resource) => (
              <Route
                key={resource.key}
                path={resource.path.replace(/^\//, '')}
                element={<ResourcePage config={resource} />}
              />
            ))}
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
