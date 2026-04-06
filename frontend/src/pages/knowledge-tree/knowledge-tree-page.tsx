import * as React from 'react'
import { useParams, Link, useSearchParams } from 'react-router-dom'
import { ArrowLeft, TreePine, Layers, Pencil } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import { useKnowledgeTreeStore } from '../../stores/knowledge-tree-store'
import { KnowledgeDocumentsTab } from './knowledge-documents-tab'
import { ContentTab } from './content-tab'
import { EditKnowledgeTreeDialog } from '../library/edit-knowledge-tree-dialog'
import type { KnowledgeTreeTab } from '../../types/knowledge-tree'

const VALID_TABS: KnowledgeTreeTab[] = ['documents', 'content']

function isValidTab(value: string | null): value is KnowledgeTreeTab {
  return VALID_TABS.includes(value as KnowledgeTreeTab)
}

const TAB_LABELS: Record<KnowledgeTreeTab, string> = {
  documents: 'Knowledge Documents',
  content: 'Content',
}

export function KnowledgeTreePage() {
  const { treeId } = useParams<{ treeId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const { trees, treesLoading, fetchTrees, chapters, fetchChapters } = useKnowledgeTreeStore()

  // Selected chapter for the documents tab (null = tree-level/overview)
  const [docsChapter, setDocsChapter] = React.useState<number | null>(null)
  // Selected chapter for the content tab (1-based, default to 1)
  const [contentChapter, setContentChapter] = React.useState<number>(1)

  const rawTab = searchParams.get('tab')
  const activeTab: KnowledgeTreeTab = isValidTab(rawTab) ? rawTab : 'documents'

  const handleTabChange = (tab: KnowledgeTreeTab) => {
    setSearchParams({ tab }, { replace: true })
  }

  // Load trees if not yet loaded
  React.useEffect(() => {
    if (trees.length === 0 && !treesLoading) {
      void fetchTrees()
    }
  }, [trees.length, treesLoading, fetchTrees])

  // Load chapters whenever treeId changes
  React.useEffect(() => {
    if (treeId) {
      void fetchChapters(treeId)
    }
  }, [treeId, fetchChapters])

  const treeChapters = treeId ? (chapters[treeId] ?? []) : []

  // Reset content chapter to first available when chapters load
  React.useEffect(() => {
    if (treeChapters.length > 0 && !treeChapters.find((c) => c.number === contentChapter)) {
      setContentChapter(treeChapters[0].number)
    }
  }, [treeChapters, contentChapter])

  const [editOpen, setEditOpen] = React.useState(false)

  const handleChaptersRefresh = () => {
    if (treeId) void fetchChapters(treeId)
  }

  if (!treeId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <p className="text-gray-500">Invalid knowledge tree URL.</p>
        <Link to="/" className="text-primary hover:underline text-sm flex items-center gap-1">
          <ArrowLeft className="h-4 w-4" /> Back to Library
        </Link>
      </div>
    )
  }

  const tree = trees.find((t) => t.id === treeId)

  if (treesLoading) {
    return (
      <div className="flex flex-col gap-4 animate-pulse">
        <div className="h-8 bg-gray-100 rounded w-64" />
        <div className="h-4 bg-gray-100 rounded w-48" />
        <div className="h-10 bg-gray-100 rounded w-full" />
        <div className="h-64 bg-gray-100 rounded w-full" />
      </div>
    )
  }

  if (!tree) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <TreePine className="h-10 w-10 text-gray-300" />
        <p className="text-gray-600 font-medium">Knowledge tree not found</p>
        <Link to="/">
          <Button variant="secondary" size="sm">
            <ArrowLeft className="h-4 w-4 mr-1" /> Back to Library
          </Button>
        </Link>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link to="/">
          <Button variant="ghost" size="sm" aria-label="Back to library">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <TreePine className="h-5 w-5 text-green-600 shrink-0" />
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-semibold text-gray-900 truncate">{tree.title}</h1>
          {tree.description && (
            <p className="text-xs text-gray-500 truncate mt-0.5">{tree.description}</p>
          )}
        </div>
        <Badge variant="neutral" className="shrink-0">
          <Layers className="h-3 w-3 mr-1" />
          {tree.num_chapters} {tree.num_chapters === 1 ? 'chapter' : 'chapters'}
        </Badge>
        <Button variant="ghost" size="sm" onClick={() => setEditOpen(true)} aria-label="Edit tree">
          <Pencil className="h-4 w-4" />
        </Button>
      </div>

      {editOpen && (
        <EditKnowledgeTreeDialog tree={tree} open={editOpen} onClose={() => setEditOpen(false)} />
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={(v) => handleTabChange(v as KnowledgeTreeTab)}>
        <TabsList>
          {VALID_TABS.map((tab) => (
            <TabsTrigger key={tab} value={tab}>
              {TAB_LABELS[tab]}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="documents">
          <KnowledgeDocumentsTab
            treeId={treeId}
            selectedChapter={docsChapter}
            chapters={treeChapters}
            onChapterChange={setDocsChapter}
            onChaptersRefresh={handleChaptersRefresh}
          />
        </TabsContent>

        <TabsContent value="content">
          <ContentTab
            treeId={treeId}
            selectedChapter={contentChapter}
            chapters={treeChapters}
            onChapterChange={setContentChapter}
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}
