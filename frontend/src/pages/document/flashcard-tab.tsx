import { useEffect, useState } from 'react'
import { Layers } from 'lucide-react'
import { client } from '../../services'
import { useFlashcardStore } from '../../stores/flashcard-store'
import { useTaskStore } from '../../stores/task-store'
import { useDocumentStore } from '../../stores/document-store'
import { Button } from '../../components/ui/button'
import { EmptyState } from '../../components/ui/empty-state'
import { TaskProgress } from './task-progress'
import { FlashcardCard } from './flashcard-card'
import { FlashcardReview } from './flashcard-review'
import { mockFlashcards } from '../../mocks/flashcards'
import type { DocumentStructureOut, FlashcardOut } from '../../types/api'
import type { FlashcardDeck } from '../../types/domain'

type CategoryFilter = 'all' | 'terminology' | 'key_facts' | 'concepts'

interface FlashcardTabProps {
  docHash: string
  chapter: number
  structure: DocumentStructureOut | null
}

export function FlashcardTab({ docHash, chapter, structure: _structure }: FlashcardTabProps) {
  const decks = useFlashcardStore((state) => state.decks)
  const activeReview = useFlashcardStore((state) => state.activeReview)
  const addDeck = useFlashcardStore((state) => state.addDeck)
  const startReview = useFlashcardStore((state) => state.startReview)

  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>('all')

  const documents = useDocumentStore((state) => state.documents)
  const doc = documents.find((d) => d.file_hash === docHash)
  const bookTitle = doc ? doc.filename.replace(/\.[^/.]+$/, '') : docHash

  // Load stored flashcards when chapter changes (if deck not already in memory)
  useEffect(() => {
    const deckKey = `${docHash}-${chapter}`
    const existingDecks = useFlashcardStore.getState().decks[deckKey]
    if (existingDecks && existingDecks.length > 0) return  // already loaded
    let cancelled = false
    void client.getStoredFlashcards(docHash, chapter).then((stored) => {
      if (cancelled || stored.length === 0) return
      const deck: FlashcardDeck = {
        documentHash: docHash,
        chapter,
        cards: stored.map((c) => ({ front: c.front, back: c.back })),
        generatedAt: stored[0].created_at,
      }
      addDeck(docHash, chapter, deck)
    })
    return () => { cancelled = true }
  }, [docHash, chapter, addDeck])

  // Subscribe to the task for this specific (docHash, chapter, type) context
  const task = useTaskStore((state) =>
    Object.values(state.tasks).find(
      (t) => t.docHash === docHash && t.chapter === chapter && t.type === 'flashcards'
    )
  )

  const isGenerating = task !== undefined && (task.status === 'pending' || task.status === 'running')
  const generateError = task?.status === 'failed' ? (task.error ?? 'Generation failed') : null

  // When the task completes, build the deck and clear the task from the store
  useEffect(() => {
    if (!task || task.status !== 'completed') return

    const flashcards = (task.result?.flashcards as FlashcardOut[] | undefined) ?? []
    const deck: FlashcardDeck = {
      documentHash: docHash,
      chapter,
      cards: flashcards.length > 0 ? flashcards : (mockFlashcards[docHash] ?? []),
      generatedAt: new Date().toISOString(),
    }

    addDeck(docHash, chapter, deck)
    useTaskStore.getState().clearTask(task.taskId)
  }, [task?.status, task?.taskId, docHash, chapter, addDeck])

  const deckKey = `${docHash}-${chapter}`
  const currentDeck = decks[deckKey]?.[0]
  const filteredCards = currentDeck
    ? categoryFilter === 'all'
      ? currentDeck.cards
      : currentDeck.cards.filter((card) => card.category === categoryFilter)
    : []

  // If there's an active review for the current chapter, show review mode
  const isReviewingCurrentChapter =
    activeReview !== null &&
    activeReview.deckIndex === `${docHash}-${chapter}`

  if (isReviewingCurrentChapter) {
    return <FlashcardReview docHash={docHash} chapter={chapter} />
  }

  const handleGenerate = async () => {
    try {
      const response = await client.generateFlashcards(chapter, bookTitle, docHash)
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

        {currentDeck && currentDeck.cards.length > 0 && !isGenerating && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => startReview(docHash, chapter)}
          >
            Start Review
          </Button>
        )}
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
              <FlashcardCard key={index} card={card} />
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
