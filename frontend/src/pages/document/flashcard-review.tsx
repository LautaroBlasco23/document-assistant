import { useState } from 'react'
import { Check, X, CheckCheck } from 'lucide-react'
import { client } from '../../services'
import { useFlashcardStore } from '../../stores/flashcard-store'
import { Button } from '../../components/ui/button'
import { FlashcardCard } from './flashcard-card'
import type { FlashcardDeck } from '../../types/domain'
import type { FlashcardOut } from '../../types/api'

interface FlashcardReviewProps {
  docHash: string
  chapter: number
  chapterIndex: number
  pendingDeck: FlashcardDeck
  onDone: () => void
}

export function FlashcardReview({
  docHash,
  chapter,
  chapterIndex,
  pendingDeck,
  onDone,
}: FlashcardReviewProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { addDeck, clearPendingDeck, removePendingCards } = useFlashcardStore.getState()
  const cards = pendingDeck.cards

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const selectAll = () => {
    setSelectedIds(new Set(cards.map((c) => c.id ?? '').filter(Boolean)))
  }

  const deselectAll = () => {
    setSelectedIds(new Set())
  }

  const handleApproveAll = async () => {
    setLoading(true)
    setError(null)
    try {
      await client.approveAllFlashcards(docHash, chapter, chapterIndex)
      // Reload approved cards and show them in normal view
      const approved = await client.getStoredFlashcards(docHash, chapter, chapterIndex)
      const deck: FlashcardDeck = {
        documentHash: docHash,
        chapter,
        cards: approved.map((c) => ({
          id: c.id,
          front: c.front,
          back: c.back,
          source_page: c.source_page ?? undefined,
          source_chunk_id: c.source_chunk_id,
          source_text: c.source_text,
        } as FlashcardOut)),
        generatedAt: approved[0]?.created_at ?? new Date().toISOString(),
      }
      addDeck(docHash, chapter, deck)
      clearPendingDeck(docHash, chapter)
      onDone()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to approve cards')
    } finally {
      setLoading(false)
    }
  }

  const handleApproveSelected = async () => {
    if (selectedIds.size === 0) return
    setLoading(true)
    setError(null)
    try {
      const ids = [...selectedIds]
      await client.approveFlashcards(docHash, ids)
      // Remove approved from pending deck; if none left, close review
      removePendingCards(docHash, chapter, ids)
      setSelectedIds(new Set())
      const remaining = useFlashcardStore.getState().pendingDecks[`${docHash}-${chapter}`]
      if (!remaining || remaining.cards.length === 0) {
        // All cards processed -- reload approved and close
        const approved = await client.getStoredFlashcards(docHash, chapter, chapterIndex)
        if (approved.length > 0) {
          const deck: FlashcardDeck = {
            documentHash: docHash,
            chapter,
            cards: approved.map((c) => ({
              id: c.id,
              front: c.front,
              back: c.back,
              source_page: c.source_page ?? undefined,
              source_chunk_id: c.source_chunk_id,
              source_text: c.source_text,
            } as FlashcardOut)),
            generatedAt: approved[0].created_at,
          }
          addDeck(docHash, chapter, deck)
        }
        clearPendingDeck(docHash, chapter)
        onDone()
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to approve cards')
    } finally {
      setLoading(false)
    }
  }

  const handleRejectSelected = async () => {
    if (selectedIds.size === 0) return
    setLoading(true)
    setError(null)
    try {
      const ids = [...selectedIds]
      await client.rejectFlashcards(docHash, ids)
      removePendingCards(docHash, chapter, ids)
      setSelectedIds(new Set())
      const remaining = useFlashcardStore.getState().pendingDecks[`${docHash}-${chapter}`]
      if (!remaining || remaining.cards.length === 0) {
        clearPendingDeck(docHash, chapter)
        onDone()
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to reject cards')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-800">Review Generated Flashcards</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            {cards.length} card{cards.length !== 1 ? 's' : ''} awaiting review
          </p>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        <Button
          variant="primary"
          size="sm"
          onClick={() => void handleApproveAll()}
          disabled={loading}
          loading={loading}
        >
          <CheckCheck className="h-3.5 w-3.5 mr-1" />
          Approve All
        </Button>

        <Button
          variant="secondary"
          size="sm"
          onClick={() => void handleApproveSelected()}
          disabled={loading || selectedIds.size === 0}
        >
          <Check className="h-3.5 w-3.5 mr-1" />
          Approve Selected ({selectedIds.size})
        </Button>

        <Button
          variant="secondary"
          size="sm"
          onClick={() => void handleRejectSelected()}
          disabled={loading || selectedIds.size === 0}
          className="text-red-600 border-red-200 hover:bg-red-50"
        >
          <X className="h-3.5 w-3.5 mr-1" />
          Reject Selected ({selectedIds.size})
        </Button>

        <div className="ml-auto flex items-center gap-2">
          <button
            className="text-xs text-primary hover:underline"
            onClick={selectAll}
          >
            Select all
          </button>
          <span className="text-gray-300">|</span>
          <button
            className="text-xs text-gray-500 hover:underline"
            onClick={deselectAll}
          >
            Deselect all
          </button>
        </div>
      </div>

      {error && <p className="text-sm text-red-500">{error}</p>}

      {/* Card grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {cards.map((card) => (
          <div key={card.id ?? card.front}>
            <FlashcardCard
              card={card}
              reviewMode
              selected={selectedIds.has(card.id ?? '')}
              onToggleSelect={toggleSelect}
            />
          </div>
        ))}
      </div>

      {cards.length === 0 && (
        <p className="text-sm text-gray-500 text-center py-6">No cards to review.</p>
      )}
    </div>
  )
}
