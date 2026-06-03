import * as React from 'react'
import { useNavigate } from 'react-router-dom'
import { X, Sparkles, PanelLeft, PanelRight, BookOpen, MessageCircleQuestion, Maximize, Minimize, ZoomIn, ZoomOut, AlignJustify, Highlighter, Trash2, Columns2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { client } from '../../services'
import { useKnowledgeTreeStore } from '../../stores/knowledge-tree-store'
import { useAppStore } from '../../stores/app-store'
import { useTaskStore } from '../../stores/task-store'
import { cn } from '../../lib/cn'
import type { KnowledgeDocument, KnowledgeChapter } from '../../types/knowledge-tree'
import { ChatPanel, type ChatPanelHandle } from './ChatPanel'
import { usePendingContent, makePendingId } from '../../stores/pending-content-store'
import type { KnowledgeTreeQuestionType } from '../../types/api'
import { PdfPagesView, type PdfPagesViewHandle } from './PdfPagesView'
import { TextPagesView, type TextPagesViewHandle } from './TextPagesView'
import { ResizeHandle } from './ResizeHandle'
import { FormatterMenu, type FormatMode } from './FormatterMenu'
import { readerMarkdownComponents } from './markdownComponents'
import { useGenerationSettings } from '../../stores/generation-settings'
import { useHighlights } from '../../stores/highlights-store'
import { useReaderPreferences, type ContentWidth } from '../../stores/reader-preferences'
import { EditableTextPanel } from './EditableTextPanel'
import { useEditGuard } from '../../hooks/use-edit-guard'

type ReadMode = 'scroll' | 'paged'

interface UnifiedDocumentReaderProps {
  doc: KnowledgeDocument
  treeId: string
  chapters: KnowledgeChapter[]
  onClose: () => void
  /** 'modal' = fullscreen overlay (default), 'page' = standalone page without overlay */
  mode?: 'modal' | 'page'
  /** Chapter number for back navigation in page mode */
  chapterNumber?: number | null
}

function loadReadMode(): ReadMode {
  try {
    const saved = localStorage.getItem('docassist_read_mode')
    if (saved === 'scroll' || saved === 'paged') return saved
  } catch { /* ignore */ }
  return 'scroll'
}

function loadLastPage(treeId: string, docId: string): number | undefined {
  try {
    const saved = localStorage.getItem(`docassist_reader_page:${treeId}:${docId}`)
    if (saved) return parseInt(saved, 10) || undefined
  } catch { /* ignore */ }
  return undefined
}

export function UnifiedDocumentReader({ doc, treeId, chapters, onClose, mode = 'modal', chapterNumber }: UnifiedDocumentReaderProps) {
  const navigate = useNavigate()
  const isPageMode = mode === 'page'

  const goBack = React.useCallback(() => {
    if (isPageMode) {
      const path = chapterNumber != null
        ? `/trees/${treeId}/chapters/${chapterNumber}`
        : `/trees/${treeId}`
      navigate(path, { replace: true })
    } else {
      onClose()
    }
  }, [isPageMode, navigate, treeId, chapterNumber, onClose])
  // Derive doc type up front — needed by useState initializers below.
  // Uses doc.file_type if set, otherwise falls back to extension detection.
  const isYouTube = doc.source_type === 'youtube'
  const fileName = (doc.source_file_name ?? doc.source_file_path ?? '').toLowerCase()
  const ft = doc.file_type
  const hasSourceFile = !!doc.source_file_path
  const _isPdfLike = !isYouTube && (ft === 'pdf' || (!ft && fileName.endsWith('.pdf')))
  const isEpub = !isYouTube && (ft === 'epub' || (!ft && fileName.endsWith('.epub')))
  const isTxt = !isYouTube && (ft === 'txt' || (!ft && fileName.endsWith('.txt')))
  const isMd = !isYouTube && (ft === 'md' || (!ft && fileName.endsWith('.md')))
  // Safety: if no source file on disk, ignore file_type=pdf — it would break the reader.
  const isTruePdf = _isPdfLike && hasSourceFile
  // Only treat as a navigable text doc if it has a source file on disk.
  // Content-only docs (e.g. highlights) use the inline renderer regardless of file_type.
  const isText = (isEpub || isTxt || isMd) && hasSourceFile
  const isContentOnly = !isYouTube && !isTruePdf && !isText && !!(doc.content ?? '').trim()
  const isHighlightsDoc = doc.title.endsWith(' — Highlights')

  const [currentPage, setCurrentPage] = React.useState<number>(1)
  const [numPages, setNumPages] = React.useState<number>(0)
  const [showLeft, setShowLeft] = React.useState(() => useReaderPreferences.getState().preferences.defaultShowLeft)
  const [showRight, setShowRight] = React.useState(() => useReaderPreferences.getState().preferences.defaultShowRight)
  const [contentWidth, setContentWidth] = React.useState(() => useReaderPreferences.getState().preferences.contentWidth)
  const [isFullscreen, setIsFullscreen] = React.useState(!isPageMode)
  const [zoom, setZoom] = React.useState(() => useReaderPreferences.getState().preferences.zoom)
  const [contextMenu, setContextMenu] = React.useState<{
    x: number
    y: number
    text: string
    chapterNumber?: number
    pageNumber?: number
    startOffset?: number
    endOffset?: number
    isTitleHighlight?: boolean
  } | null>(null)
  const [textActiveChapter, setTextActiveChapter] = React.useState<number | null>(null)

  // Read mode and resume-page state
  const [readMode, setReadMode] = React.useState<ReadMode>(loadReadMode)
  // initialPos drives both PdfPagesView (page number) and TextPagesView (chapter number).
  // For chapter-scoped PDFs we do NOT use doc.page_start: the backend extracts each chapter
  // into its own file (pages re-indexed 1-to-N), so the parent-book page number is invalid.
  // For EPUB/TXT chapter docs fall back to doc.chapter_number so the right chapter opens.
  const [initialPos, setInitialPos] = React.useState<number | undefined>(() =>
    loadLastPage(treeId, doc.id) ?? (isText ? (doc.chapter_number ?? undefined) : undefined)
  )
  const [readerKey, setReaderKey] = React.useState(0)

  const isTextRef = React.useRef(isText)
  isTextRef.current = isText
  const isTruePdfRef = React.useRef(isTruePdf)
  isTruePdfRef.current = isTruePdf
  const textActiveChapterRef = React.useRef(textActiveChapter)
  textActiveChapterRef.current = textActiveChapter
  const currentPageRef = React.useRef(currentPage)
  currentPageRef.current = currentPage

  const savePageTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null)

  const savePosition = React.useCallback((pos: number) => {
    if (savePageTimerRef.current) clearTimeout(savePageTimerRef.current)
    savePageTimerRef.current = setTimeout(() => {
      try {
        localStorage.setItem(`docassist_reader_page:${treeId}:${doc.id}`, String(pos))
      } catch { /* ignore */ }
    }, 1000)
  }, [treeId, doc.id])

  const handlePageChange = React.useCallback((page: number) => {
    setCurrentPage(page)
    savePosition(page)
  }, [savePosition])

  const handleTextChapterChange = React.useCallback((chapter: number) => {
    setTextActiveChapter(chapter)
    savePosition(chapter)
  }, [savePosition])

  const handleModeChange = React.useCallback((newMode: ReadMode, textChapter: number | null) => {
    setReadMode(newMode)
    setInitialPos(textChapter !== null ? textChapter : currentPage)
    setReaderKey((k) => k + 1)
    try { localStorage.setItem('docassist_read_mode', newMode) } catch { /* ignore */ }
  }, [currentPage])

  const cycleContentWidth = React.useCallback(() => {
    setContentWidth((prev) => {
      const order: Array<ContentWidth> = ['comfortable', 'wide', 'full']
      const idx = order.indexOf(prev)
      for (let i = 1; i <= order.length; i++) {
        const next = order[(idx + i) % order.length]
        const available =
          next === 'comfortable' ? true :
          next === 'wide' ? (!showLeft || !showRight) :
          (!showLeft && !showRight)
        if (available) {
          useReaderPreferences.getState().update({ contentWidth: next })
          return next
        }
      }
      return prev
    })
  }, [showLeft, showRight])

  const overlayRef = React.useRef<HTMLDivElement>(null)
  const pdfScrollRef = React.useRef<PdfPagesViewHandle | null>(null)
  const textScrollRef = React.useRef<TextPagesViewHandle | null>(null)
  const chatPanelRef = React.useRef<ChatPanelHandle | null>(null)
  const pendingAdd = usePendingContent((s) => s.add)
  const pendingUpdate = usePendingContent((s) => s.update)
  const pendingRemove = usePendingContent((s) => s.remove)
  const { settings: genSettings } = useGenerationSettings()
  const addError = useAppStore((s) => s.addError)
  const improveDocument = useKnowledgeTreeStore((s) => s.improveDocument)
  const addHighlight = useHighlights((s) => s.add)
  const removeHighlight = useHighlights((s) => s.remove)
  const highlightDocIds = useHighlights((s) => s.highlightDocIds)
  const setHighlightDocId = useHighlights((s) => s.setHighlightDocId)
  const clearHighlightDocId = useHighlights((s) => s.clearHighlightDocId)
  const docHighlights = useHighlights((s) => s.highlights[doc.id] ?? [])
  const createDocument = useKnowledgeTreeStore((s) => s.createDocument)
  const updateDocument = useKnowledgeTreeStore((s) => s.updateDocument)
  const revertDocument = useKnowledgeTreeStore((s) => s.revertDocument)
  const [isImproving, setIsImproving] = React.useState(false)
  const [improveTaskId, setImproveTaskId] = React.useState<string | null>(null)
  const submitTask = useTaskStore((s) => s.submitTask)
  const clearTask = useTaskStore((s) => s.clearTask)

  // --- Manual edit state ---
  const [isEditing, setIsEditing] = React.useState(false)
  const [draftContent, setDraftContent] = React.useState<string>('')
  const [isSaving, setIsSaving] = React.useState(false)
  const [editError, setEditError] = React.useState<string | null>(null)
  // Snapshot state guards: we set this the first time the user enters edit mode
  // for a given doc so the baseline-snapshot PUT runs at most once.
  const [baselineCaptured, setBaselineCaptured] = React.useState(false)
  // For non-text docs (content-only, YouTube), the prop `doc` doesn't update after
  // improve/revert because the parent state isn't wired to the store. Track it locally.
  const [currentDocOverride, setCurrentDocOverride] = React.useState<KnowledgeDocument | null>(null)

  const [leftWidth, setLeftWidth] = React.useState(() => {
    try {
      const saved = localStorage.getItem('docassist_panel_width:left')
      if (saved) return Math.max(160, Math.min(500, parseInt(saved, 10)))
    } catch { /* ignore */ }
    return 224
  })
  const [rightWidth, setRightWidth] = React.useState(() => {
    try {
      const saved = localStorage.getItem('docassist_panel_width:right')
      if (saved) return Math.max(200, Math.min(800, parseInt(saved, 10)))
    } catch { /* ignore */ }
    return 320
  })

  const startLeftWidthRef = React.useRef(leftWidth)
  const startRightWidthRef = React.useRef(rightWidth)

  const applyLeftWidth = React.useCallback((w: number) => {
    setLeftWidth(Math.max(160, Math.min(500, w)))
  }, [])

  const saveLeftWidth = React.useCallback(() => {
    try { localStorage.setItem('docassist_panel_width:left', String(leftWidth)) } catch { /* ignore */ }
  }, [leftWidth])

  const applyRightWidth = React.useCallback((w: number) => {
    setRightWidth(Math.max(200, Math.min(800, w)))
  }, [])

  const saveRightWidth = React.useCallback(() => {
    try { localStorage.setItem('docassist_panel_width:right', String(rightWidth)) } catch { /* ignore */ }
  }, [rightWidth])

  // Only record a resume entry for source/main docs (chapter_number == null).
  // Chapter docs are scoped slices and shouldn't overwrite the parent book's position.
  React.useEffect(() => {
    if ((!isTruePdf && !isText) || doc.chapter_number !== null) return
    try {
      localStorage.setItem(`docassist_last_doc:${treeId}`, doc.id)
    } catch { /* ignore */ }
  }, [treeId, doc.id, doc.chapter_number, isTruePdf, isText])
  // effectiveDoc tracks the post-improve/revert state for non-text docs whose prop doesn't
  // auto-update from the store (content-only and YouTube branches render from doc.content directly).
  const effectiveDoc = currentDocOverride ?? doc
  const showFormatter = isText || isContentOnly || (isYouTube && !!(doc.content ?? '').trim())
  const fileUrl = client.getDocumentFileUrl(treeId, doc.id)

  const contentWidthClass = contentWidth === 'full' ? '' : contentWidth === 'wide' ? 'max-w-5xl' : 'max-w-3xl'

  // When this doc is a chapter-bound document, restrict sidebar and page range
  // to that chapter only. Source/main docs show the full book.
  const isChapterScope = !isYouTube && doc.chapter_number !== null

  const allDocs = useKnowledgeTreeStore((s) => s.documents[`${treeId}:all`] ?? [])
  const chapterDocs = React.useMemo(() => {
    return allDocs
      .filter((d) => d.chapter_number !== null)
      .sort((a, b) => (a.chapter_number ?? 0) - (b.chapter_number ?? 0))
  }, [allDocs])

  // Scoped variants: limited to one chapter when opened from a chapter doc.
  const scopedChapters = React.useMemo(
    () => isChapterScope ? chapters.filter((c) => c.number === doc.chapter_number) : chapters,
    [isChapterScope, chapters, doc.chapter_number]
  )
  const scopedChapterDocs = React.useMemo(
    () => isChapterScope ? chapterDocs.filter((d) => d.chapter_number === doc.chapter_number) : chapterDocs,
    [isChapterScope, chapterDocs, doc.chapter_number]
  )

  // Format mode: resolved from the active chapter doc (for EPUB/TXT chapter trees)
  // or from the top-level doc for tree-level text docs.
  // Persisted per treeId:docId in localStorage; defaults to 'markdown' when already improved.
  const activeChapterDoc = React.useMemo(() => {
    if (!isText) return null
    if (textActiveChapter !== null) return scopedChapterDocs.find((d) => d.chapter_number === textActiveChapter) ?? null
    return null
  }, [isText, textActiveChapter, scopedChapterDocs])

  const resolvedDoc: KnowledgeDocument = (activeChapterDoc as KnowledgeDocument | null) ?? effectiveDoc

  function loadFormatMode(docId: string): FormatMode {
    try {
      const saved = localStorage.getItem(`docassist_format_mode:${treeId}:${docId}`)
      if (saved === 'plain' || saved === 'markdown') return saved
    } catch { /* ignore */ }
    return null as unknown as FormatMode
  }

  const [formatMode, setFormatMode] = React.useState<FormatMode>(() => {
    // Explicit file_type determines default rendering — overrides localStorage
    if (ft === 'md') return 'markdown'
    if (ft === 'txt' || ft === 'epub') return 'plain'
    // No explicit file_type: use saved preference, then original_content heuristic
    const saved = loadFormatMode(doc.id)
    if (saved) return saved
    if (doc.original_content !== null) return 'markdown'
    return 'plain'
  })

  // When the active chapter doc changes, update format mode if not explicitly stored
  const prevResolvedDocIdRef = React.useRef<string>(resolvedDoc.id)
  React.useEffect(() => {
    if (resolvedDoc.id === prevResolvedDocIdRef.current) return
    prevResolvedDocIdRef.current = resolvedDoc.id
    if (resolvedDoc.file_type === 'md') { setFormatMode('markdown'); return }
    if (resolvedDoc.file_type === 'txt' || resolvedDoc.file_type === 'epub') { setFormatMode('plain'); return }
    const saved = loadFormatMode(resolvedDoc.id)
    setFormatMode(saved ?? (resolvedDoc.original_content !== null ? 'markdown' : 'plain'))
  }, [resolvedDoc.id, resolvedDoc.original_content, resolvedDoc.file_type])

  const handleFormatModeChange = React.useCallback((mode: FormatMode) => {
    setFormatMode(mode)
    try { localStorage.setItem(`docassist_format_mode:${treeId}:${resolvedDoc.id}`, mode) } catch { /* ignore */ }
  }, [treeId, resolvedDoc.id])

  const handleImproveFormatting = React.useCallback(async () => {
    setIsImproving(true)
    try {
      const taskId = await improveDocument(treeId, resolvedDoc.id, resolvedDoc.chapter_number ?? null, 'formatting')
      submitTask({
        taskId,
        type: 'kt_improve',
        entityId: treeId,
        chapter: resolvedDoc.chapter_number ?? 0,
        entityTitle: `Improve formatting: ${resolvedDoc.title}`,
      })
      setImproveTaskId(taskId)
      handleFormatModeChange('markdown')
    } catch (e) {
      addError((e as Error).message || 'Failed to improve formatting. Please try again.')
      setIsImproving(false)
    }
  }, [treeId, resolvedDoc.id, resolvedDoc.chapter_number, resolvedDoc.title, improveDocument, submitTask, handleFormatModeChange, addError])

  const handleImproveText = React.useCallback(async () => {
    setIsImproving(true)
    try {
      const taskId = await improveDocument(treeId, resolvedDoc.id, resolvedDoc.chapter_number ?? null, 'text')
      submitTask({
        taskId,
        type: 'kt_improve',
        entityId: treeId,
        chapter: resolvedDoc.chapter_number ?? 0,
        entityTitle: `Improve text: ${resolvedDoc.title}`,
      })
      setImproveTaskId(taskId)
      handleFormatModeChange('markdown')
    } catch (e) {
      addError((e as Error).message || 'Failed to improve text. Please try again.')
      setIsImproving(false)
    }
  }, [treeId, resolvedDoc.id, resolvedDoc.chapter_number, resolvedDoc.title, improveDocument, submitTask, handleFormatModeChange, addError])

  const handleRevert = React.useCallback(async () => {
    setIsImproving(true)
    try {
      const reverted = await revertDocument(treeId, resolvedDoc.id, resolvedDoc.chapter_number ?? null)
      if (!isText) setCurrentDocOverride(reverted)
      handleFormatModeChange('plain')
    } catch (e) {
      addError((e as Error).message || 'Failed to revert document. Please try again.')
    } finally {
      setIsImproving(false)
    }
  }, [treeId, resolvedDoc.id, resolvedDoc.chapter_number, isText, revertDocument, handleFormatModeChange, addError])

  // --- Manual edit handlers ---
  const isDirty = isEditing && draftContent !== resolvedDoc.content

  // Reset edit state when the resolved doc identity changes (chapter switch, doc reload).
  React.useEffect(() => {
    setIsEditing(false)
    setDraftContent('')
    setIsSaving(false)
    setEditError(null)
    setBaselineCaptured(false)
  }, [resolvedDoc.id])

  // Browser unload guard while there is an unsaved draft.
  useEditGuard(isEditing && isDirty)

  const handleEnterEdit = React.useCallback(async () => {
    if (isEditing) return
    setEditError(null)
    setDraftContent(resolvedDoc.content ?? '')
    setIsEditing(true)
    // Snapshot baseline (only when no AI improvement baseline exists yet).
    if (!baselineCaptured && resolvedDoc.original_content == null) {
      try {
        await updateDocument(
          resolvedDoc.id,
          resolvedDoc.title,
          resolvedDoc.content ?? '',
          treeId,
          resolvedDoc.chapter_number ?? null,
          undefined,
          resolvedDoc.content ?? ''
        )
        setBaselineCaptured(true)
      } catch (e) {
        // Snapshot failure must not block the user from editing. We surface
        // the error and proceed; the user can still save their draft.
        addError(`Could not capture pre-edit baseline: ${(e as Error).message || 'unknown error'}`)
      }
    } else {
      setBaselineCaptured(true)
    }
  }, [isEditing, baselineCaptured, resolvedDoc, treeId, updateDocument, addError])

  const handleSaveEdit = React.useCallback(async () => {
    if (!isEditing || isSaving) return
    setIsSaving(true)
    setEditError(null)
    try {
      const updated = await updateDocument(
        resolvedDoc.id,
        resolvedDoc.title,
        draftContent,
        treeId,
        resolvedDoc.chapter_number ?? null
      )
      if (!isText) setCurrentDocOverride(updated)
      setIsEditing(false)
      setDraftContent('')
    } catch (e) {
      setEditError((e as Error).message || 'Failed to save changes. Please try again.')
    } finally {
      setIsSaving(false)
    }
  }, [isEditing, isSaving, resolvedDoc, treeId, draftContent, updateDocument, isText])

  const handleCancelEdit = React.useCallback(() => {
    if (isSaving) return
    setIsEditing(false)
    setDraftContent('')
    setEditError(null)
  }, [isSaving])

  const improveTaskEntry = useTaskStore((s) => (improveTaskId ? (s.tasks[improveTaskId] ?? null) : null))

  React.useEffect(() => {
    if (!improveTaskId || !improveTaskEntry) return
    if (improveTaskEntry.status === 'completed') {
      if (improveTaskEntry.result) {
        const updatedDoc = improveTaskEntry.result as unknown as KnowledgeDocument
        setCurrentDocOverride(updatedDoc)
      }
      setIsImproving(false)
      clearTask(improveTaskId)
      setImproveTaskId(null)
    } else if (improveTaskEntry.status === 'failed') {
      addError(improveTaskEntry.error ?? 'Improvement failed')
      setIsImproving(false)
      clearTask(improveTaskId)
      setImproveTaskId(null)
    } else if (improveTaskEntry.status === 'rate_limited') {
      const retryAfter = (improveTaskEntry.result as { retry_after?: number } | null)?.retry_after
      addError(
        retryAfter
          ? `AI provider is rate-limiting. Please retry in ${Math.ceil(retryAfter)}s.`
          : (improveTaskEntry.error ?? 'Rate limited by AI provider.')
      )
      setIsImproving(false)
      clearTask(improveTaskId)
      setImproveTaskId(null)
    }
  }, [improveTaskId, improveTaskEntry?.status, clearTask, addError])

  const visiblePages = React.useMemo(() => {
    // Chapter-scoped PDFs are served as individually-extracted files (pages re-indexed
    // 1-to-N), so page_start/page_end from the parent book are not valid page numbers
    // in that file. Only apply page filtering for the source/main doc view.
    if (!isTruePdf || isChapterScope || scopedChapterDocs.length === 0) return null
    const pages: number[] = []
    const sorted = [...scopedChapterDocs].sort((a, b) => (a.page_start ?? 0) - (b.page_start ?? 0))
    for (const chDoc of sorted) {
      if (chDoc.page_start && chDoc.page_end) {
        for (let p = chDoc.page_start; p <= chDoc.page_end; p++) {
          pages.push(p)
        }
      }
    }
    return pages.length > 0 ? pages : null
  }, [scopedChapterDocs, isTruePdf, isChapterScope])

  const activeChapter = React.useMemo(() => {
    if (isText) return textActiveChapter
    if (!isTruePdf || !currentPage) return null
    const chDoc = scopedChapterDocs.find(
      (d) => d.page_start && d.page_end && currentPage >= d.page_start && currentPage <= d.page_end
    )
    if (chDoc) return chDoc.chapter_number
    if (scopedChapterDocs.length > 0 && currentPage < (scopedChapterDocs[0].page_start ?? 0)) {
      return scopedChapterDocs[0].chapter_number
    }
    if (scopedChapterDocs.length > 0 && currentPage > (scopedChapterDocs[scopedChapterDocs.length - 1].page_end ?? 0)) {
      return scopedChapterDocs[scopedChapterDocs.length - 1].chapter_number
    }
    return null
  }, [currentPage, scopedChapterDocs, isTruePdf, isText, textActiveChapter])

  const getContext = React.useCallback((): Promise<string> => {
    if (activeChapter !== null) {
      const chDoc = scopedChapterDocs.find((d) => d.chapter_number === activeChapter)
      return Promise.resolve(chDoc?.content ?? '')
    }
    return Promise.resolve(doc.content ?? '')
  }, [activeChapter, scopedChapterDocs, doc.content])

  const scrollToChapter = (chapterNumber: number) => {
    if (isText) {
      textScrollRef.current?.scrollToChapter(chapterNumber)
      return
    }
    const chDoc = scopedChapterDocs.find((d) => d.chapter_number === chapterNumber)
    if (chDoc?.page_start) {
      pdfScrollRef.current?.scrollToPage(chDoc.page_start)
    }
  }

  const HEADING_TAGS = ['H1', 'H2', 'H3', 'H4', 'H5', 'H6']

  const handleContextMenu = (e: React.MouseEvent) => {
    const selection = window.getSelection()
    const selectedText = selection?.toString()?.trim() ?? ''
    if (!selectedText) return
    e.preventDefault()

    let startOffset: number | undefined
    let endOffset: number | undefined
    let isTitleHighlight = false
    if (selection && selection.rangeCount > 0) {
      const range = selection.getRangeAt(0)
      let container: Node | null = range.commonAncestorContainer
      while (container && !(container instanceof HTMLElement && (container.tagName === 'P' || container.tagName === 'PRE' || HEADING_TAGS.includes(container.tagName)))) {
        container = container.parentNode
      }
      if (!(container instanceof HTMLElement)) {
        container = range.commonAncestorContainer
        while (container && !(container instanceof HTMLElement && container.classList.contains('textLayer'))) {
          container = container.parentNode
        }
      }
      if (container instanceof HTMLElement) {
        if (HEADING_TAGS.includes(container.tagName)) {
          isTitleHighlight = true
        }
        const preRange = document.createRange()
        preRange.selectNodeContents(container)
        preRange.setEnd(range.startContainer, range.startOffset)
        startOffset = preRange.toString().length
        preRange.setEnd(range.endContainer, range.endOffset)
        endOffset = preRange.toString().length
      }
    }

    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      text: selectedText,
      chapterNumber: isText ? (textActiveChapter ?? undefined) : undefined,
      pageNumber: isTruePdf ? currentPage : undefined,
      startOffset,
      endOffset,
      isTitleHighlight,
    })
  }

  const openContentTab = () => {
    setShowRight(true)
    chatPanelRef.current?.showContent()
  }

  const handleMakeFlashcard = async () => {
    if (!contextMenu) return
    const chapter = activeChapter ?? doc.chapter_number ?? 1
    const text = contextMenu.text
    const id = makePendingId()
    setContextMenu(null)
    window.getSelection()?.removeAllRanges()
    pendingAdd({
      id,
      kind: 'flashcard',
      status: 'generating',
      chapter,
      front: '',
      back: '',
      sourceText: text,
    })
    openContentTab()
    try {
      const draft = await client.draftFlashcard(treeId, chapter, text, undefined, genSettings.agent_id)
      pendingUpdate(id, {
        status: 'ready',
        front: draft.front,
        back: draft.back,
        sourceText: draft.source_text,
      })
    } catch (e) {
      pendingUpdate(id, { status: 'error', error: (e as Error).message || 'Generation failed' })
      setTimeout(() => pendingRemove(id), 4000)
    }
  }

  const handleMakeQuestion = async (questionType: KnowledgeTreeQuestionType) => {
    if (!contextMenu) return
    const chapter = activeChapter ?? doc.chapter_number ?? 1
    const text = contextMenu.text
    const id = makePendingId()
    setContextMenu(null)
    window.getSelection()?.removeAllRanges()
    pendingAdd({
      id,
      kind: 'question',
      status: 'generating',
      chapter,
      questionType,
      questionData: {},
      sourceText: text,
    })
    openContentTab()
    try {
      const draft = await client.draftQuestion(treeId, chapter, questionType, text, undefined, genSettings.agent_id)
      pendingUpdate(id, { status: 'ready', questionData: draft.question_data })
    } catch (e) {
      pendingUpdate(id, { status: 'error', error: (e as Error).message || 'Generation failed' })
      setTimeout(() => pendingRemove(id), 4000)
    }
  }

  const handleAskDefinition = () => {
    if (!contextMenu) return
    const text = contextMenu.text
    setContextMenu(null)
    window.getSelection()?.removeAllRanges()
    setShowRight(true)
    chatPanelRef.current?.askInChat(text)
  }

  const hideContextMenu = () => setContextMenu(null)

  const saveHighlightDocRef = React.useRef<(text: string) => Promise<void>>()
  saveHighlightDocRef.current = async (text: string) => {
    const chapterNum = activeChapter ?? doc.chapter_number ?? 1
    const highlightsTitle = `${doc.title} — Highlights`
    const entry = text.split('\n').map((line) => `> ${line}`).join('\n')

    const storedDocId = highlightDocIds[doc.id]
    const allDocs = [
      ...(useKnowledgeTreeStore.getState().documents[`${treeId}:all`] ?? []),
      ...(useKnowledgeTreeStore.getState().documents[`${treeId}:${chapterNum}`] ?? []),
    ]

    let existing = storedDocId ? allDocs.find((d) => d.id === storedDocId) : undefined
    if (!existing) {
      existing = allDocs.find((d) => d.chapter_number === chapterNum && d.title === highlightsTitle)
    }

    try {
      if (existing) {
        setHighlightDocId(doc.id, existing.id)
        await updateDocument(
          existing.id,
          existing.title,
          existing.content ? `${existing.content}\n\n---\n\n${entry}` : entry,
          treeId,
          chapterNum,
        )
      } else {
        const created = await createDocument(treeId, chapterNum, highlightsTitle, entry)
        setHighlightDocId(doc.id, created.id)
      }
    } catch (e) {
      // If the stored doc was deleted, clear the stale ID and try once more
      if (storedDocId) {
        clearHighlightDocId(doc.id)
        try {
          const created = await createDocument(treeId, chapterNum, highlightsTitle, entry)
          setHighlightDocId(doc.id, created.id)
        } catch {
          addError('Failed to save highlight to document')
        }
      } else {
        addError((e as Error).message || 'Failed to save highlight to document')
      }
    }
  }

  const handleHighlight = (text: string, pos?: { chapterNumber?: number; pageNumber?: number; startOffset?: number; endOffset?: number; isTitleHighlight?: boolean }) => {
    if (isHighlightsDoc) return
    addHighlight(doc.id, text, pos)
    setContextMenu(null)
    window.getSelection()?.removeAllRanges()
    void saveHighlightDocRef.current!(text)
  }

  const handleDeleteHighlight = (text: string, pos?: { startOffset?: number; endOffset?: number }) => {
    const matches = docHighlights.filter((h) => {
      if (h.text.toLowerCase() !== text.toLowerCase()) return false
      if (pos?.startOffset !== undefined && h.startOffset !== pos.startOffset) return false
      if (pos?.endOffset !== undefined && h.endOffset !== pos.endOffset) return false
      return true
    })
    for (const h of matches) removeHighlight(doc.id, h.id)
    setContextMenu(null)
    window.getSelection()?.removeAllRanges()
  }

  const zoomIn = React.useCallback(() => setZoom((z) => {
    const next = Math.min(2, +(z + 0.1).toFixed(1))
    useReaderPreferences.getState().update({ zoom: next })
    return next
  }), [])
  const zoomOut = React.useCallback(() => setZoom((z) => {
    const next = Math.max(0.5, +(z - 0.1).toFixed(1))
    useReaderPreferences.getState().update({ zoom: next })
    return next
  }), [])

  const zoomInRef = React.useRef(zoomIn)
  zoomInRef.current = zoomIn
  const zoomOutRef = React.useRef(zoomOut)
  zoomOutRef.current = zoomOut
  const handleHighlightRef = React.useRef(handleHighlight)
  handleHighlightRef.current = handleHighlight
  const goBackRef = React.useRef(goBack)
  goBackRef.current = goBack

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (!isPageMode && isFullscreen) {
          setIsFullscreen(false)
        } else {
          goBackRef.current()
        }
        return
      }
      const activeEl = document.activeElement
      const isInput =
        activeEl instanceof HTMLInputElement ||
        activeEl instanceof HTMLTextAreaElement ||
        (activeEl as HTMLElement)?.isContentEditable

      if (!isInput) {
        if (e.key === '+' || e.key === '=') {
          e.preventDefault()
          zoomInRef.current()
          return
        }
        if (e.key === '-') {
          e.preventDefault()
          zoomOutRef.current()
          return
        }
      }
      if (e.ctrlKey && e.key === 'a') {
        if (!isInput) {
          const selection = window.getSelection()
          const selected = selection?.toString()?.trim() ?? ''
          if (selected) {
            e.preventDefault()
            let startOffset: number | undefined
            let endOffset: number | undefined
            let isTitleHighlight = false
            if (selection && selection.rangeCount > 0) {
              const range = selection.getRangeAt(0)
              let container: Node | null = range.commonAncestorContainer
              while (container && !(container instanceof HTMLElement && (container.tagName === 'P' || container.tagName === 'PRE' || HEADING_TAGS.includes(container.tagName)))) {
                container = container.parentNode
              }
              if (!(container instanceof HTMLElement)) {
                container = range.commonAncestorContainer
                while (container && !(container instanceof HTMLElement && container.dataset.page)) {
                  container = container.parentNode
                }
              }
              if (container instanceof HTMLElement) {
                if (HEADING_TAGS.includes(container.tagName)) {
                  isTitleHighlight = true
                }
                const preRange = document.createRange()
                preRange.selectNodeContents(container)
                preRange.setEnd(range.startContainer, range.startOffset)
                startOffset = preRange.toString().length
                preRange.setEnd(range.endContainer, range.endOffset)
                endOffset = preRange.toString().length
              }
            }
            handleHighlightRef.current(selected, {
              chapterNumber: isTextRef.current ? (textActiveChapterRef.current ?? undefined) : undefined,
              pageNumber: isTruePdfRef.current ? currentPageRef.current : undefined,
              startOffset,
              endOffset,
              isTitleHighlight,
            })
          }
        }
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isFullscreen, isPageMode])

  const topBar = (
    <>
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-surface-200 dark:border-surface-200 shrink-0 bg-surface-100 dark:bg-surface-100">
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <h2 className="text-sm font-semibold text-text-primary truncate">{doc.title}</h2>
          {activeChapter !== null && (
            <span className="text-xs px-2 py-0.5 bg-primary-light dark:bg-primary/12 text-primary rounded-full shrink-0">
              {scopedChapters.find((c) => c.number === activeChapter)?.title ?? `Chapter ${activeChapter}`}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {/* Page / chapter progress */}
          {isTruePdf && numPages > 0 && (
            <span className="text-xs tabular-nums text-text-tertiary select-none">
              {currentPage} / {numPages}
            </span>
          )}
          {isText && scopedChapters.length > 0 && textActiveChapter !== null && (
            <span className="text-xs tabular-nums text-text-tertiary select-none">
              Ch {textActiveChapter} / {scopedChapters.length}
            </span>
          )}

          {/* Zoom controls */}
          {(isTruePdf || isText || isContentOnly || isYouTube) && (
            <div className="flex items-center gap-0.5 bg-surface dark:bg-surface-200 rounded-md shadow-sm border border-surface-200 dark:border-surface-200 px-1.5 py-0.5">
              <button
                onClick={zoomOut}
                disabled={zoom <= 0.5}
                className="p-0.5 rounded text-text-tertiary hover:text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                aria-label="Zoom out"
                title="Zoom out"
              >
                <ZoomOut className="h-3.5 w-3.5" />
              </button>
              <span className="text-xs tabular-nums text-text-tertiary min-w-[3ch] text-center select-none">
                {Math.round(zoom * 100)}%
              </span>
              <button
                onClick={zoomIn}
                disabled={zoom >= 2}
                className="p-0.5 rounded text-text-tertiary hover:text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                aria-label="Zoom in"
                title="Zoom in"
              >
                <ZoomIn className="h-3.5 w-3.5" />
              </button>
            </div>
          )}

          {/* Read mode toggle */}
          {(isTruePdf || isText || isContentOnly || isYouTube) && (
            <div className="flex items-center gap-0.5 bg-surface dark:bg-surface-200 rounded-md shadow-sm border border-surface-200 dark:border-surface-200 px-0.5 py-0.5">
              <button
                onClick={() => readMode !== 'scroll' && handleModeChange('scroll', textActiveChapter)}
                className={cn(
                  'p-1 rounded transition-colors',
                  readMode === 'scroll'
                    ? 'bg-primary-light dark:bg-primary/20 text-primary'
                    : 'text-text-tertiary hover:text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100'
                )}
                aria-label="Scroll mode"
                title="Scroll mode — continuous pages"
              >
                <AlignJustify className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => readMode !== 'paged' && handleModeChange('paged', textActiveChapter)}
                className={cn(
                  'p-1 rounded transition-colors',
                  readMode === 'paged'
                    ? 'bg-primary-light dark:bg-primary/20 text-primary'
                    : 'text-text-tertiary hover:text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100'
                )}
                aria-label="Paged mode"
                title="Paged mode — one page at a time (← →)"
              >
                <BookOpen className="h-3.5 w-3.5" />
              </button>
            </div>
          )}

          {/* Formatter menu — all text-content docs (EPUB, TXT, content-only, YouTube) */}
          {showFormatter && (
            <FormatterMenu
              mode={formatMode}
              isImproved={resolvedDoc.original_content !== null}
              isImproving={isImproving}
              onModeChange={handleFormatModeChange}
              onImprove={handleImproveText}
              onImproveFormatting={handleImproveFormatting}
              onRevert={handleRevert}
              isEditing={isEditing}
              isSaving={isSaving}
              isDirty={isDirty}
              onEnterEdit={handleEnterEdit}
              onSave={handleSaveEdit}
              onCancel={handleCancelEdit}
              canEdit={!isImproving}
            />
          )}
        </div>

        <div className="flex items-center gap-1 flex-1 justify-end">
          {!isPageMode && (
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-1.5 rounded-md transition-colors text-text-tertiary hover:text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100"
              aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
              title={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
            >
              {isFullscreen ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
            </button>
          )}
          {!isHighlightsDoc && (isTruePdf || isText) && (
            <button
              onClick={() => setShowLeft(!showLeft)}
              className={cn(
                'p-1.5 rounded-md transition-colors',
                showLeft
                  ? 'text-primary bg-primary-light hover:bg-primary-light dark:bg-primary/12 dark:hover:bg-primary/12'
                  : 'text-text-tertiary hover:text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100'
              )}
              aria-label="Toggle chapter sidebar"
              title="Toggle chapter sidebar"
            >
              <PanelLeft className="h-4 w-4" />
            </button>
          )}
          {!isHighlightsDoc && (
            <button
              onClick={() => setShowRight(!showRight)}
              className={cn(
                'p-1.5 rounded-md transition-colors',
                showRight
                  ? 'text-primary bg-primary-light hover:bg-primary-light dark:bg-primary/12 dark:hover:bg-primary/12'
                  : 'text-text-tertiary hover:text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100'
              )}
              aria-label="Toggle chat panel"
              title="Toggle chat & notes"
            >
              <PanelRight className="h-4 w-4" />
            </button>
          )}
          {!isHighlightsDoc && (
            <button
              onClick={cycleContentWidth}
              className={cn(
                'p-1.5 rounded-md transition-colors',
                contentWidth !== 'comfortable'
                  ? 'text-primary bg-primary-light hover:bg-primary-light dark:bg-primary/12 dark:hover:bg-primary/12'
                  : 'text-text-tertiary hover:text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100'
              )}
              aria-label="Content width"
              title={
                contentWidth === 'comfortable' ? 'Comfortable width' :
                contentWidth === 'wide' ? 'Wider width' :
                'Full width'
              }
            >
              <Columns2 className="h-4 w-4" />
            </button>
          )}
            <button
              onClick={goBack}
              className="p-1.5 text-text-tertiary hover:text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100 rounded-md transition-colors ml-2"
            aria-label="Close reader"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </>
  )

  const contentArea = (
    <>
      {/* Content area */}
      <div className="flex-1 min-h-0 flex">
        {/* Left panel: Chapter sidebar */}
        {!isHighlightsDoc && (isTruePdf || isText) && (
          <>
            <div
              className={cn(
                'border-r border-surface-200 dark:border-surface-200 bg-surface-100 dark:bg-surface-100 transition-all duration-300 ease-in-out overflow-hidden',
                showLeft ? 'block' : 'hidden'
              )}
              style={{ width: showLeft ? leftWidth : 0 }}
            >
              <div className="h-full flex flex-col">
                <div className="px-3 py-2 border-b border-surface-200 dark:border-surface-200">
                  <h3 className="text-xs font-semibold text-text-tertiary uppercase tracking-wide">Chapters</h3>
                </div>
                <div className="flex-1 overflow-y-auto">
                  {scopedChapters.map((ch) => {
                    const isActive = activeChapter === ch.number
                    const chDoc = scopedChapterDocs.find((d) => d.chapter_number === ch.number)
                    return (
                      <button
                        key={ch.number}
                        onClick={() => scrollToChapter(ch.number)}
                        className={cn(
                          'w-full text-left px-3 py-2 text-sm transition-colors flex items-center gap-2',
                          isActive
                            ? 'bg-primary-light dark:bg-primary/12 text-primary font-medium'
                            : 'text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100'
                        )}
                      >
                        <BookOpen className="h-3.5 w-3.5 shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="truncate">{ch.title}</div>
                          {isTruePdf && chDoc?.page_start && (
                            <div className="text-xs text-text-tertiary">
                              Page {chDoc.page_start}
                              {chDoc.page_end && chDoc.page_end !== chDoc.page_start
                                ? ` - ${chDoc.page_end}`
                                : ''}
                            </div>
                          )}
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>
            </div>
            {showLeft && (
              <ResizeHandle
                onResizeStart={() => { startLeftWidthRef.current = leftWidth }}
                onResize={(delta) => applyLeftWidth(startLeftWidthRef.current + delta)}
                onResizeEnd={saveLeftWidth}
              />
            )}
          </>
        )}

        {/* Center: Document content */}
        {isTruePdf ? (
          <PdfPagesView
            key={readerKey}
            fileUrl={fileUrl}
            visiblePages={visiblePages}
            zoom={zoom}
            mode={readMode}
            initialPage={initialPos}
            contentWidth={contentWidth}
            onCurrentPageChange={handlePageChange}
            onNumPagesChange={setNumPages}
            onContextMenu={handleContextMenu}
            onClickAway={hideContextMenu}
            scrollRef={pdfScrollRef}
            highlights={docHighlights}
          />
        ) : isText ? (
          <TextPagesView
            key={readerKey}
            chapters={scopedChapters}
            chapterDocs={scopedChapterDocs}
            zoom={zoom}
            mode={readMode}
            formatMode={formatMode}
            contentWidth={contentWidth}
            initialChapter={initialPos}
            onCurrentChapterChange={handleTextChapterChange}
            onContextMenu={handleContextMenu}
            onClickAway={hideContextMenu}
            scrollRef={textScrollRef}
            isTxt={isTxt}
            highlights={docHighlights}
            isEditing={isEditing}
            draftContent={draftContent}
            isSaving={isSaving}
            editError={editError}
            onDraftChange={setDraftContent}
            editingChapter={textActiveChapter ?? resolvedDoc.chapter_number ?? null}
          />
        ) : isYouTube ? (
          <div
            className="flex-1 min-w-0 bg-surface-100 dark:bg-bg-inset overflow-auto"
            onContextMenu={handleContextMenu}
            onClick={hideContextMenu}
          >
            <div
              className={cn('mx-auto py-8 px-6 text-text-secondary text-md', contentWidthClass)}
              style={{ fontSize: `${Math.round(zoom * 100)}%` }}
            >
              {isEditing ? (
                <EditableTextPanel
                  value={draftContent}
                  fileType={effectiveDoc.file_type ?? null}
                  isSaving={isSaving}
                  error={editError}
                  supportsPreview={formatMode === 'markdown'}
                  onChange={setDraftContent}
                />
              ) : formatMode === 'markdown' ? (
                <div
                  className="font-reading space-y-reader-para"
                  style={{ lineHeight: 'var(--reader-line-height)' }}
                >
                  <ReactMarkdown components={readerMarkdownComponents}>{effectiveDoc.content ?? ''}</ReactMarkdown>
                </div>
              ) : (
                <p
                  className="font-reading whitespace-pre-wrap break-words"
                  style={{ lineHeight: 'var(--reader-line-height)' }}
                >
                  {effectiveDoc.content}
                </p>
              )}
            </div>
          </div>
        ) : (
          <div
            className="flex-1 min-w-0 bg-surface-100 dark:bg-bg-inset overflow-auto"
            onContextMenu={handleContextMenu}
            onClick={hideContextMenu}
          >
            {effectiveDoc.content ? (
              <div
                className={cn('mx-auto py-8 px-6 text-text-secondary text-md', contentWidthClass)}
                style={{ fontSize: `${Math.round(zoom * 100)}%` }}
              >
                {isEditing ? (
                  <EditableTextPanel
                    value={draftContent}
                    fileType={effectiveDoc.file_type ?? null}
                    isSaving={isSaving}
                    error={editError}
                    supportsPreview={formatMode === 'markdown'}
                    onChange={setDraftContent}
                  />
                ) : formatMode === 'markdown' ? (
                  <div
                    className="font-reading space-y-reader-para"
                    style={{ lineHeight: 'var(--reader-line-height)' }}
                  >
                    <ReactMarkdown components={readerMarkdownComponents}>{effectiveDoc.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p
                    className="font-reading whitespace-pre-wrap break-words"
                    style={{ lineHeight: 'var(--reader-line-height)' }}
                  >
                    {effectiveDoc.content}
                  </p>
                )}
              </div>
            ) : (
              <div className="flex items-center justify-center h-full">
                <p className="text-sm text-text-tertiary">No content available.</p>
              </div>
            )}
          </div>
        )}

        {/* Right panel: Chat & Notes */}
        {!isHighlightsDoc && showRight && (
          <ResizeHandle
            onResizeStart={() => { startRightWidthRef.current = rightWidth }}
            onResize={(delta) => applyRightWidth(startRightWidthRef.current - delta)}
            onResizeEnd={saveRightWidth}
          />
        )}
        {!isHighlightsDoc && (
          <div
            className={cn(
              'border-l border-surface-200 dark:border-surface-200 transition-all duration-300 ease-in-out overflow-hidden',
              showRight ? 'block' : 'hidden'
            )}
            style={{ width: showRight ? rightWidth : 0 }}
          >
            <div className="h-full">
              <ChatPanel
                ref={chatPanelRef}
                getContext={getContext}
                storageKey={`${treeId}:${doc.id}:unified`}
                treeId={treeId}
                chapter={activeChapter}
                docId={doc.id}
                docTitle={doc.title}
              />
            </div>
          </div>
        )}
      </div>

      {/* Context menu */}
      {!isHighlightsDoc && contextMenu && (
        <div
          className="fixed z-[60] bg-surface dark:bg-surface-200 rounded-lg shadow-lg border border-surface-200 dark:border-surface-200 py-1 min-w-[200px]"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          {docHighlights.some((h) => {
            if (h.text.toLowerCase() !== contextMenu.text.toLowerCase()) return false
            if (contextMenu.startOffset !== undefined && h.startOffset !== contextMenu.startOffset) return false
            if (contextMenu.endOffset !== undefined && h.endOffset !== contextMenu.endOffset) return false
            if (h.isTitleHighlight !== (contextMenu.isTitleHighlight ?? false)) return false
            return true
          }) ? (
            <button
              onClick={() => handleDeleteHighlight(contextMenu.text, { startOffset: contextMenu.startOffset, endOffset: contextMenu.endOffset })}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors"
            >
              <Trash2 className="h-3.5 w-3.5 text-error" />
              Delete highlight
            </button>
          ) : (
            <button
              onClick={() => handleHighlight(contextMenu.text, { chapterNumber: contextMenu.chapterNumber, pageNumber: contextMenu.pageNumber, startOffset: contextMenu.startOffset, endOffset: contextMenu.endOffset, isTitleHighlight: contextMenu.isTitleHighlight })}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors"
            >
              <Highlighter className="h-3.5 w-3.5 text-yellow-500" />
              Highlight
            </button>
          )}
          <div className="my-1 border-t border-surface-200 dark:border-surface-200" />
          <div className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-text-tertiary">
            Ask
          </div>
          <button
            onClick={handleAskDefinition}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors"
          >
            <MessageCircleQuestion className="h-3.5 w-3.5 text-accent" />
            Ask definition in chat
          </button>
          <div className="my-1 border-t border-surface-200 dark:border-surface-200" />
          <div className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-text-tertiary">
            Generate
          </div>
          <button
            onClick={handleMakeFlashcard}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors"
          >
            <Sparkles className="h-3.5 w-3.5 text-ai" />
            Flashcard
          </button>
          <button
            onClick={() => handleMakeQuestion('true_false')}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors"
          >
            <Sparkles className="h-3.5 w-3.5 text-ai" />
            True / False question
          </button>
          <button
            onClick={() => handleMakeQuestion('multiple_choice')}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors"
          >
            <Sparkles className="h-3.5 w-3.5 text-ai" />
            Multiple choice question
          </button>
          <button
            onClick={() => handleMakeQuestion('checkbox')}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-surface-100 dark:hover:bg-surface-100 transition-colors"
          >
            <Sparkles className="h-3.5 w-3.5 text-ai" />
            Select all that apply
          </button>
        </div>
      )}
    </>
  )

  if (isPageMode) {
    return (
      <div className="flex flex-col h-screen bg-surface dark:bg-surface animate-fade-in">
        {topBar}
        {contentArea}
      </div>
    )
  }

  return (
    <div
      ref={overlayRef}
      className={cn(
        'fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm',
        isFullscreen ? 'p-0' : 'p-4'
      )}
      onClick={(e) => {
        if (e.target === overlayRef.current) goBack()
      }}
    >
      <div
        className={cn(
          'w-full h-full bg-surface dark:bg-surface flex flex-col overflow-hidden animate-fade-in',
          isFullscreen
            ? 'max-h-full max-w-full rounded-none shadow-none'
            : 'max-h-[95vh] max-w-[1600px] rounded-xl shadow-2xl'
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {topBar}
        {contentArea}
      </div>
    </div>
  )
}
