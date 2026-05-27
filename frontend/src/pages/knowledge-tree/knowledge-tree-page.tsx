import * as React from 'react'
import { useParams, Link, useSearchParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, TreePine, Layers, Pencil, Plus, FileText, BookMarked, Check, X, Trash2, FolderOpen, Download, BookOpenCheck } from 'lucide-react'
import { cn } from '../../lib/cn'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { ConfirmDialog } from '../../components/ui/confirm-dialog'
import { useKnowledgeTreeStore } from '../../stores/knowledge-tree-store'
import { useAppStore } from '../../stores/app-store'
import { client } from '../../services'
import { KnowledgeDocumentsTab } from './knowledge-documents-tab'
import { AllDocumentsTab } from './all-documents-tab'
import { ContentTab } from './content-tab'
import { StudyTab } from './study-tab'
import { ExamTab } from './exam-tab'
import { EditKnowledgeTreeDialog } from '../library/edit-knowledge-tree-dialog'
import type { KnowledgeChapter, KnowledgeTreeTab } from '../../types/knowledge-tree'

const VALID_TABS: KnowledgeTreeTab[] = ['documents', 'content', 'study', 'exam']

const TAB_LABELS: Record<KnowledgeTreeTab, string> = {
  documents: 'Knowledge Documents',
  content: 'Content',
  study: 'Study',
  exam: 'Exam',
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
  const { createChapter, updateChapter, deleteChapter, deleteChapters, markChapterRead } = useKnowledgeTreeStore()

  const [editingChapter, setEditingChapter] = React.useState<{ number: number; title: string } | null>(null)
  const [showNewChapter, setShowNewChapter] = React.useState(false)
  const [newChapterTitle, setNewChapterTitle] = React.useState('')
  const [creatingChapter, setCreatingChapter] = React.useState(false)
  const [deleteChapterOpen, setDeleteChapterOpen] = React.useState(false)
  const [deletingChapterNumber, setDeletingChapterNumber] = React.useState<number | null>(null)
  const [deletingChapter, setDeletingChapter] = React.useState(false)

  const [selectedChapters, setSelectedChapters] = React.useState<Set<number>>(new Set())
  const [bulkDeleteOpen, setBulkDeleteOpen] = React.useState(false)
  const [bulkDeleting, setBulkDeleting] = React.useState(false)

  const toggleChapterSelection = (number: number) => {
    setSelectedChapters((prev) => {
      const next = new Set(prev)
      if (next.has(number)) {
        next.delete(number)
      } else {
        next.add(number)
      }
      return next
    })
  }

  const toggleSelectAll = () => {
    setSelectedChapters((prev) => {
      if (prev.size === chapters.length) {
        return new Set()
      }
      return new Set(chapters.map((c) => c.number))
    })
  }

  const handleBulkDelete = () => {
    setBulkDeleteOpen(true)
  }

  const handleConfirmBulkDelete = async () => {
    if (selectedChapters.size === 0) return
    setBulkDeleting(true)
    try {
      await deleteChapters(treeId, Array.from(selectedChapters))
      if (selectedChapter !== null && selectedChapters.has(selectedChapter)) {
        onChapterChange(null)
      }
      setSelectedChapters(new Set())
      onChaptersRefresh()
    } finally {
      setBulkDeleting(false)
      setBulkDeleteOpen(false)
    }
  }

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

  const handleDeleteChapter = (chapterNumber: number) => {
    setDeletingChapterNumber(chapterNumber)
    setDeleteChapterOpen(true)
  }

  const handleConfirmDeleteChapter = async () => {
    if (deletingChapterNumber === null) return
    setDeletingChapter(true)
    try {
      await deleteChapter(treeId, deletingChapterNumber)
      onChapterChange(null)
      onChaptersRefresh()
    } finally {
      setDeletingChapter(false)
      setDeleteChapterOpen(false)
      setDeletingChapterNumber(null)
    }
  }

  return (
    <aside className="w-52 shrink-0 flex flex-col gap-1">
      {/* General */}
      <p className="text-xs font-medium text-text-tertiary uppercase tracking-wide px-2 mb-1">General</p>

      <button
        onClick={onSelectAllDocuments}
        className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm text-left w-full transition-colors sidebar-border-green ${
          showAllDocuments
            ? 'bg-success-light dark:bg-success/12 text-success font-medium'
            : 'text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100'
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
            : 'text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100'
        }`}
      >
        <BookMarked className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate">Overview</span>
      </button>

      {/* Divider */}
      <div className="border-t border-surface-200 dark:border-surface-200 my-2" />

      {/* Chapters */}
      <p className="text-xs font-medium text-text-tertiary uppercase tracking-wide px-2 mb-1">Chapters</p>

      {/* Select all */}
      <div className="flex items-center gap-2 px-1 py-1">
        <button
          type="button"
          onClick={toggleSelectAll}
          className="flex items-center gap-2 text-sm text-text-secondary hover:text-gray-900 dark:hover:text-slate-100 transition-colors"
        >
          <div
            className={cn(
              'w-4 h-4 rounded border-2 flex items-center justify-center transition-colors',
              selectedChapters.size === chapters.length && chapters.length > 0
                ? 'bg-primary border-primary'
                : 'border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200',
            )}
          >
            {selectedChapters.size === chapters.length && chapters.length > 0 && (
              <Check className="h-2.5 w-2.5 text-white" />
            )}
          </div>
          <span className="text-xs">Select all</span>
        </button>
      </div>

      {/* Bulk action bar */}
      {selectedChapters.size > 0 && (
        <div className="flex items-center gap-2 px-1 py-1.5 border-b border-surface-200 dark:border-surface-200 mb-1">
          <span className="text-xs text-text-tertiary flex-1">
            {selectedChapters.size} of {chapters.length} selected
          </span>
          <Button
            size="sm"
            variant="destructive"
            onClick={handleBulkDelete}
            className="h-6 text-xs"
          >
            <Trash2 className="h-3 w-3 mr-1" />
            Delete
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setSelectedChapters(new Set())}
            className="h-6 text-xs"
          >
            Clear
          </Button>
        </div>
      )}

      {chapters.map((ch) => (
        <div
          key={ch.number}
          className={`group flex flex-col rounded-md ${
            ch.status === 'read' ? 'bg-green-50 dark:bg-green-950/20' : ''
          }`}
        >
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
              <button type="submit" className="p-1 text-success hover:text-green-700 rounded" aria-label="Save">
                <Check className="h-3 w-3" />
              </button>
              <button type="button" onClick={() => setEditingChapter(null)} className="p-1 text-text-tertiary hover:text-text-secondary rounded" aria-label="Cancel">
                <X className="h-3 w-3" />
              </button>
            </form>
          ) : (
            <div className="flex items-center">
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); toggleChapterSelection(ch.number) }}
                className={cn(
                  'p-1 rounded transition-opacity',
                  selectedChapters.size > 0
                    ? 'opacity-100'
                    : 'opacity-0 group-hover:opacity-100',
                )}
                aria-label={`Select chapter ${ch.title}`}
              >
                <div
                  className={cn(
                    'w-4 h-4 rounded border-2 flex items-center justify-center transition-colors',
                    selectedChapters.has(ch.number)
                      ? 'bg-primary border-primary'
                      : 'border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200',
                  )}
                >
                  {selectedChapters.has(ch.number) && (
                    <Check className="h-2.5 w-2.5 text-white" />
                  )}
                </div>
              </button>
              <button
                onClick={() => onChapterChange(ch.number)}
                className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm text-left flex-1 min-w-0 transition-colors ${
                  selectedChapter === ch.number && !showAllDocuments
                    ? 'bg-primary-light dark:bg-primary/12 text-primary font-medium'
                    : 'text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100'
                }`}
              >
                <FileText className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate">{ch.title}</span>
              </button>
              {ch.status === 'read' ? (
                <BookOpenCheck className="h-3 w-3 mr-1 text-success shrink-0" />
              ) : (
                <button
                  onClick={() => void markChapterRead(treeId, ch.number)}
                  className="opacity-0 group-hover:opacity-100 p-1 text-text-tertiary hover:text-success transition-opacity rounded"
                  aria-label={`Mark chapter ${ch.title} as read`}
                >
                  <Check className="h-3 w-3" />
                </button>
              )}
              <button
                onClick={() => setEditingChapter({ number: ch.number, title: ch.title })}
                className="opacity-0 group-hover:opacity-100 p-1 text-text-tertiary hover:text-gray-700 dark:hover:text-slate-200 transition-opacity rounded"
                aria-label={`Rename chapter ${ch.title}`}
              >
                <Pencil className="h-3 w-3" />
              </button>
              <button
                onClick={() => void handleDeleteChapter(ch.number)}
                className="opacity-0 group-hover:opacity-100 p-1 text-text-tertiary hover:text-red-500 transition-opacity mr-1 rounded"
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
          className="flex items-center gap-2 px-3 py-2 rounded-md text-sm text-text-tertiary hover:text-gray-700 dark:hover:text-slate-200 hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors w-full text-left"
        >
          <Plus className="h-3.5 w-3.5" />
          New Chapter
        </button>
      )}

      <ConfirmDialog
        open={deleteChapterOpen}
        onOpenChange={setDeleteChapterOpen}
        title="Delete chapter?"
        description={deletingChapterNumber !== null ? `Delete "${chapters.find((c) => c.number === deletingChapterNumber)?.title ?? deletingChapterNumber}"? All its documents will be removed.` : ''}
        confirmLabel="Delete"
        cancelLabel="Cancel"
        variant="destructive"
        loading={deletingChapter}
        onConfirm={handleConfirmDeleteChapter}
      />
      <ConfirmDialog
        open={bulkDeleteOpen}
        onOpenChange={setBulkDeleteOpen}
        title={`Delete ${selectedChapters.size} chapters?`}
        description={`Delete ${selectedChapters.size === 1 ? '"' + (chapters.find((c) => c.number === Array.from(selectedChapters)[0])?.title ?? '') + '"' : selectedChapters.size + ' chapters'}? All their documents will be removed.`}
        confirmLabel="Delete"
        cancelLabel="Cancel"
        variant="destructive"
        loading={bulkDeleting}
        onConfirm={handleConfirmBulkDelete}
      />
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
  const [showAllDocuments, setShowAllDocuments] = React.useState(true)

  const rawTab = searchParams.get('tab')
  const activeTab: KnowledgeTreeTab = isValidTab(rawTab) ? rawTab : 'documents'

  const resumeDocId = searchParams.get('resume') === 'true' && treeId
    ? (localStorage.getItem(`docassist_last_doc:${treeId}`) ?? undefined)
    : undefined

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
  const [exporting, setExporting] = React.useState(false)

  const handleExport = async () => {
    if (!treeId || !tree) return
    setExporting(true)
    try {
      const blob = await client.exportKnowledgeTree(treeId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${tree.title}.zip`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      addError('Export failed. Please try again.')
    } finally {
      setExporting(false)
    }
  }

  const handleChaptersRefresh = () => {
    if (treeId) void fetchChapters(treeId)
  }

  if (!treeId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <p className="text-text-tertiary">Invalid knowledge tree URL.</p>
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
        <TreePine className="h-5 w-5 text-success shrink-0" />
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-semibold text-text-primary truncate">{tree.title}</h1>
          {tree.description && (
            <p className="text-xs text-text-tertiary truncate mt-0.5">{tree.description}</p>
          )}
        </div>
        <Badge variant="neutral" className="shrink-0">
          <Layers className="h-3 w-3 mr-1" />
          {tree.num_chapters} {tree.num_chapters === 1 ? 'chapter' : 'chapters'}
        </Badge>
        <Button variant="ghost" size="sm" onClick={() => setEditOpen(true)} aria-label="Edit tree">
          <Pencil className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="sm" onClick={() => void handleExport()} disabled={exporting} aria-label="Export tree">
          <Download className="h-4 w-4" />
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
              resumeDocId={resumeDocId}
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

              <TabsContent value="study">
                <StudyTab
                  treeId={treeId}
                  selectedChapter={selectedChapter}
                  chapters={treeChapters}
                />
              </TabsContent>

              <TabsContent value="exam">
                <ExamTab
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
