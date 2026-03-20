import { useState } from 'react'
import { Layers } from 'lucide-react'
import { useFlashcardStore } from '../../stores/flashcard-store'
import { useDocumentStore } from '../../stores/document-store'
import { Button } from '../../components/ui/button'
import { Progress } from '../../components/ui/progress'
import { EmptyState } from '../../components/ui/empty-state'
import { Tooltip } from '../../components/ui/tooltip'
import { FlashcardCard } from './flashcard-card'
import { FlashcardReview } from './flashcard-review'
import { mockFlashcards } from '../../mocks/flashcards'
import type { DocumentStructureOut } from '../../types/api'

interface FlashcardTabProps {
  docHash: string
  chapter?: number
  structure: DocumentStructureOut | null
}

export function FlashcardTab({ docHash, chapter, structure: _structure }: FlashcardTabProps) {
  const decks = useFlashcardStore((state) => state.decks)
  const activeReview = useFlashcardStore((state) => state.activeReview)
  const generateDeck = useFlashcardStore((state) => state.generateDeck)
  const startReview = useFlashcardStore((state) => state.startReview)

  const documents = useDocumentStore((state) => state.documents)
  const doc = documents.find((d) => d.file_hash === docHash)
  const bookTitle = doc ? doc.filename.replace(/\.[^/.]+$/, '') : docHash

  const [generating, setGenerating] = useState(false)
  const [generateError, setGenerateError] = useState<string | null>(null)

  const deckKey = chapter !== undefined ? `${docHash}-${chapter}` : null
  const currentDeck = deckKey ? (decks[deckKey] ?? [])[0] : undefined

  // If there's an active review for the current chapter, show review mode
  const isReviewingCurrentChapter =
    activeReview !== null &&
    chapter !== undefined &&
    activeReview.deckIndex === `${docHash}-${chapter}`

  if (isReviewingCurrentChapter && chapter !== undefined) {
    return <FlashcardReview docHash={docHash} chapter={chapter} />
  }

  const handleGenerate = async () => {
    if (chapter === undefined) return
    setGenerating(true)
    setGenerateError(null)

    try {
      // generateDeck handles polling and stores the result in the store.
      // After the task completes it checks result.flashcards; if empty, falls
      // back to an empty array. We patch in mock data here for demo mode.
      await generateDeck(docHash, chapter, bookTitle)

      // If the deck ended up empty (mock client returns no flashcards in result),
      // inject the mock flashcards directly into the store.
      const key = `${docHash}-${chapter}`
      const storedDeck = useFlashcardStore.getState().decks[key]?.[0]
      if (storedDeck && storedDeck.cards.length === 0) {
        const fallback = mockFlashcards[docHash] ?? []
        useFlashcardStore.setState((state) => ({
          decks: {
            ...state.decks,
            [key]: [{ ...storedDeck, cards: fallback }],
          },
        }))
      }
    } catch (err) {
      setGenerateError(err instanceof Error ? err.message : 'Generation failed')
    } finally {
      setGenerating(false)
    }
  }

  const isDisabled = chapter === undefined

  const generateButton = (
    <Button
      variant="primary"
      size="sm"
      onClick={() => void handleGenerate()}
      disabled={isDisabled || generating}
      loading={generating}
    >
      Generate Flashcards
    </Button>
  )

  return (
    <div className="flex flex-col gap-4">
      {/* Toolbar */}
      <div className="flex items-center gap-3">
        {isDisabled ? (
          <Tooltip content="Select a specific chapter first">
            <span>{generateButton}</span>
          </Tooltip>
        ) : (
          generateButton
        )}

        {currentDeck && currentDeck.cards.length > 0 && !generating && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => chapter !== undefined && startReview(docHash, chapter)}
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
      {generating && (
        <div className="flex flex-col gap-2">
          <Progress indeterminate />
          <p className="text-xs text-gray-400">Generating flashcards...</p>
        </div>
      )}

      {/* Card grid */}
      {!generating && currentDeck && currentDeck.cards.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {currentDeck.cards.map((card, index) => (
            <FlashcardCard key={index} card={card} />
          ))}
        </div>
      )}

      {/* Empty states */}
      {!generating && !currentDeck && (
        <EmptyState
          icon={Layers}
          title={isDisabled ? 'Select a chapter' : 'No flashcards yet'}
          description={
            isDisabled
              ? 'Choose a specific chapter to generate flashcards'
              : 'Generate flashcards to start reviewing this chapter'
          }
        />
      )}

      {!generating && currentDeck && currentDeck.cards.length === 0 && (
        <EmptyState
          icon={Layers}
          title="No cards generated"
          description="Try selecting a different chapter or regenerating"
        />
      )}
    </div>
  )
}
