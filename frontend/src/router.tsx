import React, { Suspense } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import { MainLayout } from './components/layout/main-layout'
import { SkeletonBlock } from './components/ui/skeleton'

const LibraryPage = React.lazy(() =>
  import('./pages/library/library-page').then((m) => ({ default: m.LibraryPage }))
)
const KnowledgeTreePage = React.lazy(() =>
  import('./pages/knowledge-tree/knowledge-tree-page').then((m) => ({ default: m.KnowledgeTreePage }))
)
const DocumentPage = React.lazy(() =>
  import('./pages/document/document-page').then((m) => ({ default: m.DocumentPage }))
)
const SettingsPage = React.lazy(() =>
  import('./pages/settings/settings-page').then((m) => ({ default: m.SettingsPage }))
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
    path: '/',
    element: <MainLayout />,
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
        path: 'documents/:hash',
        element: (
          <Suspense fallback={<PageFallback />}>
            <DocumentPage />
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
