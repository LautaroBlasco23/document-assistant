import * as React from 'react'
import { useParams, Link, useSearchParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, TreePine, Layers, Pencil, Plus, FileText, BookMarked, Check, X, Trash2, FolderOpen } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { useKnowledgeTreeStore } from '../../stores/knowledge-tree-store'
import { useAppStore } from '../../stores/app-store'
import { KnowledgeDocumentsTab } from './knowledge-documents-tab'
import { AllDocumentsTab } from './all-documents-tab'
import { ContentTab } from './content-tab'
import { EditKnowledgeTreeDialog } from '../library/edit-knowledge-tree-dialog'
import type { KnowledgeChapter, KnowledgeTreeTab } from '../../types/knowledge-tree'

const VALID_TABS: KnowledgeTreeTab[] = ['documents', 'content']

const TAB_LABELS: Record<KnowledgeTreeTab, string> = {
  documents: 'Knowledge Documents',
  content: 'Content',
}

function isValidTab(value: string | null): value is KnowledgeTreeTab {
  return VALID_TABS.includes(value as KnowledgeTreeTab)
}

// ─── Sections sidebar ─────────────────────────────────────────────────────────

interface SectionsSidebarProps {
  treeId: string
  chapters: KnowledgeChapter[]
  selectedChapter: number | null
  showAllDocuments: boolean
  onSelectAllDocuments: () => void
  onChapterChange: (chapter: number | null) => void
  onChaptersRefresh: () => void
}

function SectionsSidebar({
  treeId,
  chapters,
  selectedChapter,
  showAllDocuments,
  onSelectAllDocuments,
  onChapterChange,
  onChaptersRefresh,
}: SectionsSidebarProps) {
  const { createChapter, updateChapter, deleteChapter } = useKnowledgeTreeStore()

  const [editingChapter, setEditingChapter] = React.useState<{ number: number; title: string } | null>(null)
  const [showNewChapter, setShowNewChapter] = React.useState(false)
  const [newChapterTitle, setNewChapterTitle] = React.useState('')
  const [creatingChapter, setCreatingChapter] = React.useState(false)

  const handleCreateChapter = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newChapterTitle.trim()) return
    setCreatingChapter(true)
    try {
      await createChapter(treeId, newChapterTitle.trim())
      setNewChapterTitle('')
      setShowNewChapter(false)
      onChaptersRefresh()
    } finally {
      setCreatingChapter(false)
    }
  }

  const handleRenameChapter = async (number: number, title: string) => {
    if (!title.trim()) return
    await updateChapter(treeId, number, title.trim())
    setEditingChapter(null)
    onChaptersRefresh()
  }

  const handleDeleteChapter = async (chapterNumber: number) => {
    const ch = chapters.find((c) => c.number === chapterNumber)
    if (!window.confirm(`Delete chapter "${ch?.title ?? chapterNumber}"? All its documents will be removed.`)) return
    await deleteChapter(treeId, chapterNumber)
    onChapterChange(null)
    onChaptersRefresh()
  }

  return (
    <aside className="w-52 shrink-0 flex flex-col gap-1">
      {/* General */}
      <p className="text-xs font-medium text-gray-400 dark:text-slate-500 uppercase tracking-wide px-2 mb-1">General</p>

      <button
        onClick={onSelectAllDocuments}
        className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm text-left w-full transition-colors sidebar-border-green ${
          showAllDocuments
            ? 'bg-success-light dark:bg-success/12 text-success font-medium'
            : 'text-gray-600 dark:text-slate-400 hover:bg-surface-100 dark:hover:bg-surface-100'
        }`}
      >
        <FolderOpen className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate">Documents</span>
      </button>

      {/* Tree-level (overview) */}
      <button
        onClick={() => onChapterChange(null)}
        className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm text-left w-full transition-colors sidebar-border-blue ${
          selectedChapter === null && !showAllDocuments
            ? 'bg-primary-light dark:bg-primary/12 text-primary font-medium'
            : 'text-gray-600 dark:text-slate-400 hover:bg-surface-100 dark:hover:bg-surface-100'
        }`}
      >
        <BookMarked className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate">Overview</span>
      </button>

      {/* Divider */}
      <div className="border-t border-surface-200 dark:border-surface-200 my-2" />

      {/* Chapters */}
      <p className="text-xs font-medium text-gray-400 dark:text-slate-500 uppercase tracking-wide px-2 mb-1">Chapters</p>

      {chapters.map((ch) => (
        <div key={ch.number} className="group flex flex-col">
          {editingChapter?.number === ch.number ? (
            <form
              onSubmit={(e) => { e.preventDefault(); void handleRenameChapter(ch.number, editingChapter.title) }}
              className="flex gap-1 px-1 py-1"
            >
              <Input
                value={editingChapter.title}
                onChange={(e) => setEditingChapter({ ...editingChapter, title: e.target.value })}
                className="text-xs h-7 flex-1"
                autoFocus
              />
              <button type="submit" className="p-1 text-green-600 hover:text-green-700 rounded" aria-label="Save">
                <Check className="h-3 w-3" />
              </button>
              <button type="button" onClick={() => setEditingChapter(null)} className="p-1 text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300 rounded" aria-label="Cancel">
                <X className="h-3 w-3" />
              </button>
            </form>
          ) : (
            <div className="flex items-center">
                <button
                  onClick={() => onChapterChange(ch.number)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm text-left flex-1 min-w-0 transition-colors ${
                    selectedChapter === ch.number && !showAllDocuments
                      ? 'bg-primary-light dark:bg-primary/12 text-primary font-medium'
                      : 'text-gray-600 dark:text-slate-400 hover:bg-surface-100 dark:hover:bg-surface-100'
                  }`}
              >
                <FileText className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate">{ch.title}</span>
              </button>
              <button
                onClick={() => setEditingChapter({ number: ch.number, title: ch.title })}
                className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 dark:text-slate-500 hover:text-gray-700 dark:hover:text-slate-200 transition-opacity rounded"
                aria-label={`Rename chapter ${ch.title}`}
              >
                <Pencil className="h-3 w-3" />
              </button>
              <button
                onClick={() => void handleDeleteChapter(ch.number)}
                className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition-opacity mr-1 rounded"
                aria-label={`Delete chapter ${ch.title}`}
              >
                <Trash2 className="h-3 w-3" />
              </button>
            </div>
          )}
        </div>
      ))}

      {/* New chapter */}
      {showNewChapter ? (
        <form onSubmit={(e) => void handleCreateChapter(e)} className="flex flex-col gap-1 px-1 pt-1">
          <Input
            value={newChapterTitle}
            onChange={(e) => setNewChapterTitle(e.target.value)}
            placeholder="Chapter title"
            autoFocus
            className="text-xs h-7"
          />
          <div className="flex gap-1">
            <Button type="submit" size="sm" variant="primary" disabled={creatingChapter || !newChapterTitle.trim()} className="flex-1 h-6 text-xs">
              Add
            </Button>
            <Button type="button" size="sm" variant="ghost" onClick={() => setShowNewChapter(false)} className="h-6 text-xs">
              <X className="h-3 w-3" />
            </Button>
          </div>
        </form>
      ) : (
        <button
          onClick={() => setShowNewChapter(true)}
          className="flex items-center gap-2 px-3 py-2 rounded-md text-sm text-gray-400 dark:text-slate-500 hover:text-gray-700 dark:hover:text-slate-200 hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors w-full text-left"
        >
          <Plus className="h-3.5 w-3.5" />
          New Chapter
        </button>
      )}
    </aside>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function KnowledgeTreePage() {
  const { treeId } = useParams<{ treeId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const addError = useAppStore((s) => s.addError)
  const { trees, treesLoading, treesFetched, fetchTrees, chapters, fetchChapters } = useKnowledgeTreeStore()

  // Single shared chapter selection (null = Overview)
  const [selectedChapter, setSelectedChapter] = React.useState<number | null>(null)
  const [showAllDocuments, setShowAllDocuments] = React.useState(false)

  const rawTab = searchParams.get('tab')
  const activeTab: KnowledgeTreeTab = isValidTab(rawTab) ? rawTab : 'documents'

  const handleTabChange = (tab: KnowledgeTreeTab) => {
    setSearchParams({ tab }, { replace: true })
  }

  const handleChapterChange = (chapter: number | null) => {
    setSelectedChapter(chapter)
    setShowAllDocuments(false)
  }

  // Load trees if not yet loaded
  React.useEffect(() => {
    if (!treesFetched && !treesLoading) {
      void fetchTrees()
    }
  }, [treesFetched, treesLoading, fetchTrees])

  // Load chapters whenever treeId changes
  React.useEffect(() => {
    if (treeId) {
      void fetchChapters(treeId)
    }
  }, [treeId, fetchChapters])

  const treeChapters = treeId ? (chapters[treeId] ?? []) : []

  const tree = trees.find((t) => t.id === treeId)

  React.useEffect(() => {
    if (treesFetched && !treesLoading && !tree) {
      addError('Knowledge tree not found.')
      void navigate('/')
    }
  }, [treesFetched, treesLoading, tree, addError, navigate])

  const [editOpen, setEditOpen] = React.useState(false)

  const handleChaptersRefresh = () => {
    if (treeId) void fetchChapters(treeId)
  }

  if (!treeId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <p className="text-gray-500 dark:text-slate-400">Invalid knowledge tree URL.</p>
        <Link to="/" className="text-primary hover:underline text-sm flex items-center gap-1">
          <ArrowLeft className="h-4 w-4" /> Back to Library
        </Link>
      </div>
    )
  }

  if (treesLoading) {
    return (
      <div className="flex flex-col gap-4 animate-pulse">
        <div className="h-8 bg-surface-200 dark:bg-surface-200 rounded w-64" />
        <div className="h-4 bg-surface-200 dark:bg-surface-200 rounded w-48" />
        <div className="h-10 bg-surface-200 dark:bg-surface-200 rounded w-full" />
        <div className="h-64 bg-surface-200 dark:bg-surface-200 rounded w-full" />
      </div>
    )
  }

  if (!tree) return null

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
          <h1 className="text-xl font-semibold text-gray-900 dark:text-slate-100 truncate">{tree.title}</h1>
          {tree.description && (
            <p className="text-xs text-gray-500 dark:text-slate-400 truncate mt-0.5">{tree.description}</p>
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

      {/* Sidebar + Tabs layout */}
      <div className="flex gap-4 min-h-0">
        <SectionsSidebar
          treeId={treeId}
          chapters={treeChapters}
          selectedChapter={selectedChapter}
          showAllDocuments={showAllDocuments}
          onSelectAllDocuments={() => setShowAllDocuments(true)}
          onChapterChange={handleChapterChange}
          onChaptersRefresh={handleChaptersRefresh}
        />

        <div className="flex-1 min-w-0">
          {showAllDocuments ? (
            <AllDocumentsTab
              treeId={treeId}
              chapters={treeChapters}
            />
          ) : selectedChapter === null ? (
            <KnowledgeDocumentsTab
              treeId={treeId}
              selectedChapter={null}
              chapters={treeChapters}
            />
          ) : (
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
                  selectedChapter={selectedChapter}
                  chapters={treeChapters}
                />
              </TabsContent>

              <TabsContent value="content">
                <ContentTab
                  treeId={treeId}
                  selectedChapter={selectedChapter}
                  chapters={treeChapters}
                />
              </TabsContent>
            </Tabs>
          )}
        </div>
      </div>
    </div>
  )
}
