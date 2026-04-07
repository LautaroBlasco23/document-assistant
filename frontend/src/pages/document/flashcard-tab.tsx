import { useEffect, useState } from 'react'
import { Layers } from 'lucide-react'
import { client } from '../../services'
import { useFlashcardStore } from '../../stores/flashcard-store'
import { useExamStore } from '../../stores/exam-store'
import { useTaskStore } from '../../stores/task-store'
import { useDocumentStore } from '../../stores/document-store'
import { Button } from '../../components/ui/button'
import { EmptyState } from '../../components/ui/empty-state'
import { TaskProgress } from './task-progress'
import { FlashcardCard } from './flashcard-card'
import { FlashcardReview } from './flashcard-review'
import type { DocumentStructureOut, FlashcardOut } from '../../types/api'
import type { FlashcardDeck } from '../../types/domain'

type CategoryFilter = 'all' | 'terminology' | 'key_facts' | 'concepts'

interface FlashcardTabProps {
  docHash: string
  chapter: number
  chapterIndex: number
  structure: DocumentStructureOut | null
}

export function FlashcardTab({ docHash, chapter, chapterIndex, structure: _structure }: FlashcardTabProps) {
  const decks = useFlashcardStore((state) => state.decks)
  const pendingDecks = useFlashcardStore((state) => state.pendingDecks)
  const addDeck = useFlashcardStore((state) => state.addDeck)
  const setPendingDeck = useFlashcardStore((state) => state.setPendingDeck)

  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>('all')

  const documents = useDocumentStore((state) => state.documents)
  const doc = documents.find((d) => d.file_hash === docHash)
  const bookTitle = doc ? doc.filename.replace(/\.[^/.]+$/, '') : docHash

  const deckKey = `${docHash}-${chapter}`
  const currentDeck = decks[deckKey]?.[0]
  const pendingDeck = pendingDecks[deckKey] ?? null

  // On mount: load approved cards OR check for pending ones
  useEffect(() => {
    let cancelled = false

    const loadCards = async () => {
      // If we already have an approved deck in memory, skip
      const existingDecks = useFlashcardStore.getState().decks[deckKey]
      const existingPending = useFlashcardStore.getState().pendingDecks[deckKey]
      if ((existingDecks && existingDecks.length > 0) || existingPending) return

      // Check for pending cards first (review screen takes priority)
      const pending = await client.getPendingFlashcards(docHash, chapter, chapterIndex)
      if (cancelled) return

      if (pending.length > 0) {
        const deck: FlashcardDeck = {
          documentHash: docHash,
          chapter,
          cards: pending.map((c) => ({
            id: c.id,
            front: c.front,
            back: c.back,
            source_page: c.source_page ?? undefined,
            source_chunk_id: c.source_chunk_id,
            source_text: c.source_text,
          } as FlashcardOut)),
          generatedAt: pending[0].created_at,
          status: 'pending',
        }
        setPendingDeck(docHash, chapter, deck)
        return
      }

      // No pending cards -- load approved ones
      const stored = await client.getStoredFlashcards(docHash, chapter, chapterIndex)
      if (cancelled || stored.length === 0) return
      const deck: FlashcardDeck = {
        documentHash: docHash,
        chapter,
        cards: stored.map((c) => ({
          id: c.id,
          front: c.front,
          back: c.back,
          source_page: c.source_page ?? undefined,
          source_chunk_id: c.source_chunk_id,
          source_text: c.source_text,
        } as FlashcardOut)),
        generatedAt: stored[0].created_at,
      }
      addDeck(docHash, chapter, deck)
    }

    void loadCards()
    return () => { cancelled = true }
  }, [docHash, chapter, chapterIndex, addDeck, setPendingDeck, deckKey])

  // Subscribe to the task for this specific (docHash, chapter, type) context
  const task = useTaskStore((state) =>
    Object.values(state.tasks).find(
      (t) => t.docHash === docHash && t.chapter === chapter && t.type === 'flashcards'
    )
  )

  const isGenerating = task !== undefined && (task.status === 'pending' || task.status === 'running')
  const generateError = task?.status === 'failed' ? (task.error ?? 'Generation failed') : null

  // When the task completes, put result into pendingDeck for review
  useEffect(() => {
    if (!task || task.status !== 'completed') return

    const flashcards = (task.result?.flashcards as FlashcardOut[] | undefined) ?? []
    const cards = flashcards.length > 0 ? flashcards : []

    const deck: FlashcardDeck = {
      documentHash: docHash,
      chapter,
      cards,
      generatedAt: new Date().toISOString(),
      status: 'pending',
    }

    setPendingDeck(docHash, chapter, deck)
    useTaskStore.getState().clearTask(task.taskId)
    // Clear exam status cache since flashcards were regenerated
    useExamStore.getState().clearChapterStatus(docHash, chapter)
  }, [task?.status, task?.taskId, docHash, chapter, task?.result, setPendingDeck])

  const filteredCards = currentDeck
    ? categoryFilter === 'all'
      ? currentDeck.cards
      : currentDeck.cards.filter((card) => card.category === categoryFilter)
    : []

  const handleGenerate = async () => {
    // Clear any previous failed task so the new one takes over immediately
    if (task?.status === 'failed') {
      useTaskStore.getState().clearTask(task.taskId)
    }
    try {
      const response = await client.generateFlashcards(chapter, chapterIndex, bookTitle, docHash, true)
      useTaskStore.getState().submitTask({
        taskId: response.task_id,
        type: 'flashcards',
        docHash,
        chapter,
        bookTitle,
      })
    } catch {
      // API call failed before task was submitted -- no cleanup needed
    }
  }

  // If there's a pending deck to review, show the review screen
  if (pendingDeck && !isGenerating) {
    return (
      <FlashcardReview
        docHash={docHash}
        chapter={chapter}
        chapterIndex={chapterIndex}
        pendingDeck={pendingDeck}
        onDone={() => {/* store is updated inside FlashcardReview */}}
      />
    )
  }

  const generateButton = (
    <Button
      variant="primary"
      size="sm"
      onClick={() => void handleGenerate()}
      disabled={isGenerating}
      loading={isGenerating}
    >
      {currentDeck && currentDeck.cards.length > 0 ? 'Regenerate Flashcards' : 'Generate Flashcards'}
    </Button>
  )

  return (
    <div className="flex flex-col gap-4">
      {/* Toolbar */}
      <div className="flex items-center gap-3">
        {generateButton}
      </div>

      {/* Generate error */}
      {generateError && (
        <p className="text-sm text-red-500">{generateError}</p>
      )}

      {/* Loading */}
      {isGenerating && (
        <TaskProgress
          progressPct={task?.progressPct ?? null}
          message={task?.progress ?? null}
          fallbackMessage="Generating flashcards..."
        />
      )}

      {/* Card grid */}
      {!isGenerating && currentDeck && currentDeck.cards.length > 0 && (
        <>
          <div className="flex items-center gap-3">
            <label htmlFor="category-filter" className="text-sm font-medium text-gray-700">
              Filter by:
            </label>
            <select
              id="category-filter"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value as CategoryFilter)}
              className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            >
              <option value="all">All Cards</option>
              <option value="terminology">Terminology</option>
              <option value="key_facts">Key Facts</option>
              <option value="concepts">Concepts</option>
            </select>
            <span className="text-sm text-gray-500">
              {filteredCards.length} {filteredCards.length === 1 ? 'card' : 'cards'}
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {filteredCards.map((card, index) => (
              <FlashcardCard key={card.id ?? index} card={card} />
            ))}
          </div>
        </>
      )}

      {/* Empty states */}
      {!isGenerating && !currentDeck && (
        <EmptyState
          icon={Layers}
          title="No flashcards yet"
          description="Generate flashcards to start reviewing this chapter"
        />
      )}

      {!isGenerating && currentDeck && currentDeck.cards.length === 0 && (
        <EmptyState
          icon={Layers}
          title="No cards generated"
          description="Try selecting a different chapter or regenerating"
        />
      )}
    </div>
  )
}
