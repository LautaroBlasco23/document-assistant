import React, { Suspense } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import { ProtectedRoute } from './components/auth/protected-route'
import { MainLayout } from './components/layout/main-layout'
import { SkeletonBlock } from './components/ui/skeleton'

// Auth pages (no lazy loading for faster initial render)
import { LoginPage } from './pages/auth/login-page'
import { RegisterPage } from './pages/auth/register-page'

const LibraryPage = React.lazy(() =>
  import('./pages/library/library-page').then((m) => ({ default: m.LibraryPage }))
)
const KnowledgeTreePage = React.lazy(() =>
  import('./pages/knowledge-tree/knowledge-tree-page').then((m) => ({ default: m.KnowledgeTreePage }))
)
const SettingsPage = React.lazy(() =>
  import('./pages/settings/settings-page').then((m) => ({ default: m.SettingsPage }))
)
const PlanPage = React.lazy(() =>
  import('./pages/settings/plan-page').then((m) => ({ default: m.PlanPage }))
)
const NotFoundPage = React.lazy(() =>
  import('./pages/not-found-page').then((m) => ({ default: m.NotFoundPage }))
)

function PageFallback() {
  return (
    <div className="flex flex-col gap-4 p-2">
      <SkeletonBlock height="h-8" className="w-48" />
      <SkeletonBlock height="h-40" />
    </div>
  )
}

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/register',
    element: <RegisterPage />,
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <MainLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: (
          <Suspense fallback={<PageFallback />}>
            <LibraryPage />
          </Suspense>
        ),
      },
      {
        path: 'trees/:treeId',
        element: (
          <Suspense fallback={<PageFallback />}>
            <KnowledgeTreePage />
          </Suspense>
        ),
      },
      {
        path: 'settings',
        element: (
          <Suspense fallback={<PageFallback />}>
            <SettingsPage />
          </Suspense>
        ),
      },
      {
        path: 'settings/plan',
        element: (
          <Suspense fallback={<PageFallback />}>
            <PlanPage />
          </Suspense>
        ),
      },
      {
        path: '*',
        element: (
          <Suspense fallback={<PageFallback />}>
            <NotFoundPage />
          </Suspense>
        ),
      },
    ],
  },
])
