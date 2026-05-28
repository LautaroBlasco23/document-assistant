import * as React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { UnifiedDocumentReader } from '../../components/reader/UnifiedDocumentReader'
import { useKnowledgeTreeStore } from '../../stores/knowledge-tree-store'
import { useAppStore } from '../../stores/app-store'
import type { KnowledgeDocument } from '../../types/knowledge-tree'

export function ViewerPage() {
  const { treeId, docId, chapterNumber: chapterParam } = useParams<{
    treeId: string
    docId: string
    chapterNumber?: string
  }>()
  const chapterNumber = chapterParam ? parseInt(chapterParam, 10) : null
  const navigate = useNavigate()
  const addError = useAppStore((s) => s.addError)
  const { chapters, fetchChapters, documents, fetchAllDocuments } = useKnowledgeTreeStore()

  const [doc, setDoc] = React.useState<KnowledgeDocument | null>(null)
  const [loading, setLoading] = React.useState(true)

  const treeChapters = treeId ? (chapters[treeId] ?? []) : []

  // Load chapters
  React.useEffect(() => {
    if (treeId) void fetchChapters(treeId)
  }, [treeId, fetchChapters])

  // Resolve document: check store first, then fetch all docs
  React.useEffect(() => {
    if (!treeId || !docId) return

    // Check if doc is already in the store
    const allDocsKey = `${treeId}:all`
    const cachedDocs = documents[allDocsKey]
    if (cachedDocs) {
      const found = cachedDocs.find((d) => d.id === docId)
      if (found) {
        setDoc(found)
        setLoading(false)
        return
      }
    }

    // Fetch all documents if not cached or not found
    const load = async () => {
      setLoading(true)
      try {
        await fetchAllDocuments(treeId)
        const updatedDocs = useKnowledgeTreeStore.getState().documents[allDocsKey] ?? []
        const found = updatedDocs.find((d) => d.id === docId)
        if (found) {
          setDoc(found)
        } else {
          addError('Document not found.')
          void navigate(backPath(), { replace: true })
        }
      } catch {
        addError('Failed to load document.')
        void navigate(backPath(), { replace: true })
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [treeId, docId, documents, fetchAllDocuments, addError, navigate])

  const backPath = () =>
    chapterNumber !== null
      ? `/trees/${treeId}/chapters/${chapterNumber}`
      : `/trees/${treeId}`

  if (!treeId || !docId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <p className="text-text-tertiary">Invalid viewer URL.</p>
        <Button variant="secondary" size="sm" onClick={() => navigate('/')}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to Library
        </Button>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex flex-col h-screen bg-surface dark:bg-surface">
        <div className="flex items-center gap-3 px-4 py-2 border-b border-surface-200 dark:border-surface-200 shrink-0 bg-surface-100 dark:bg-surface-100">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(backPath())}
            aria-label="Back to tree"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="h-4 bg-surface-200 dark:bg-surface-200 rounded w-48 animate-pulse" />
        </div>
        <div className="flex-1 flex items-center justify-center">
          <p className="text-sm text-text-tertiary">Loading document...</p>
        </div>
      </div>
    )
  }

  if (!doc) return null

  return (
    <UnifiedDocumentReader
      doc={doc}
      treeId={treeId}
      chapters={treeChapters}
      onClose={() => navigate(backPath())}
      chapterNumber={chapterNumber}
      mode="page"
    />
  )
}
