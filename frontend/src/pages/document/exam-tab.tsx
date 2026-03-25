import { useEffect, useState, useCallback } from 'react'
import { GraduationCap } from 'lucide-react'
import { useFlashcardStore } from '../../stores/flashcard-store'
import { useExamStore } from '../../stores/exam-store'
import { Button } from '../../components/ui/button'
import { EmptyState } from '../../components/ui/empty-state'
import { ExamSession } from './exam-session'
import type { DocumentStructureOut } from '../../types/api'

interface ExamTabProps {
  docHash: string
  chapter: number
  qdrantIndex: number
  structure: DocumentStructureOut | null
}

type BadgeVariant = 'none' | 'completed' | 'gold' | 'platinum'

function LevelBadge({ level }: { level: number }) {
  const variant = (
    level === 1 ? 'completed' :
    level === 2 ? 'gold' :
    level === 3 ? 'platinum' :
    'none'
  ) as BadgeVariant

  if (variant === 'none') {
    return (
      <span className="inline-flex items-center rounded-full bg-gray-100 px-3 py-1 text-sm font-medium text-gray-500">
        Not started
      </span>
    )
  }

  const styles: Record<Exclude<BadgeVariant, 'none'>, string> = {
    completed: 'bg-green-100 text-green-800',
    gold: 'bg-amber-100 text-amber-800',
    platinum: 'bg-slate-200 text-slate-700',
  }

  const labels: Record<Exclude<BadgeVariant, 'none'>, string> = {
    completed: 'Completed',
    gold: 'Gold',
    platinum: 'Platinum',
  }

  return (
    <span className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${styles[variant]}`}>
      {labels[variant]}
    </span>
  )
}

function formatCountdown(ms: number): string {
  if (ms <= 0) return '0s'
  const totalSeconds = Math.floor(ms / 1000)
  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60

  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${minutes}m`
  if (minutes > 0) return `${minutes}m ${seconds}s`
  return `${seconds}s`
}

export function ExamTab({ docHash, chapter, qdrantIndex: _qdrantIndex, structure: _structure }: ExamTabProps) {
  const decks = useFlashcardStore((state) => state.decks)
  const activeExam = useExamStore((state) => state.activeExam)
  const chapterStatus = useExamStore((state) => state.chapterStatus)
  const fetchSingleChapterStatus = useExamStore((state) => state.fetchSingleChapterStatus)
  const startExam = useExamStore((state) => state.startExam)

  const [countdown, setCountdown] = useState<string | null>(null)

  const deckKey = `${docHash}-${chapter}`
  const currentDeck = decks[deckKey]?.[0]
  const hasCards = currentDeck && currentDeck.cards.length > 0

  const status = chapterStatus[deckKey]

  // Fetch chapter exam status on mount and when chapter/docHash changes
  useEffect(() => {
    void fetchSingleChapterStatus(docHash, chapter)
  }, [docHash, chapter, fetchSingleChapterStatus])

  // Countdown timer
  const updateCountdown = useCallback(() => {
    if (!status?.cooldown_until) {
      setCountdown(null)
      return
    }
    const remaining = new Date(status.cooldown_until).getTime() - Date.now()
    if (remaining <= 0) {
      setCountdown(null)
      // Cooldown expired, re-fetch status
      void fetchSingleChapterStatus(docHash, chapter)
    } else {
      setCountdown(formatCountdown(remaining))
    }
  }, [status?.cooldown_until, docHash, chapter, fetchSingleChapterStatus])

  useEffect(() => {
    if (!status?.cooldown_until) {
      setCountdown(null)
      return
    }
    updateCountdown()
    const interval = setInterval(updateCountdown, 1000)
    return () => clearInterval(interval)
  }, [status?.cooldown_until, updateCountdown])

  // If there's an active exam for this chapter, show the exam session
  if (activeExam && activeExam.docHash === docHash && activeExam.chapter === chapter) {
    return <ExamSession />
  }

  // No flashcards state
  if (!hasCards) {
    return (
      <EmptyState
        icon={GraduationCap}
        title="No flashcards yet"
        description="Generate flashcards first from the Flashcards tab to take an exam."
      />
    )
  }

  const cardCount = currentDeck.cards.length
  const level = status?.level ?? 0
  const canTake = status?.can_take_exam ?? true

  return (
    <div className="flex flex-col gap-6">
      {/* Level status */}
      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium text-gray-600">Current level</p>
        <LevelBadge level={level} />
      </div>

      {/* Exam info */}
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 flex flex-col gap-3">
        <p className="text-sm text-gray-600">
          This exam has <span className="font-semibold text-gray-800">{cardCount}</span>{' '}
          {cardCount === 1 ? 'question' : 'questions'}. You must answer all correctly to pass.
        </p>

        {!canTake && countdown !== null && (
          <p className="text-sm text-amber-700 bg-amber-50 rounded-md px-3 py-2 border border-amber-200">
            Next exam available in: <span className="font-semibold">{countdown}</span>
          </p>
        )}

        <Button
          variant="primary"
          size="sm"
          disabled={!canTake}
          onClick={() => startExam(docHash, chapter, currentDeck.cards)}
          className="self-start"
        >
          Start Exam
        </Button>
      </div>

      {level > 0 && (
        <p className="text-xs text-gray-400">
          {level === 1 && 'Pass the exam again to reach Gold level.'}
          {level === 2 && 'Pass the exam again to reach Platinum level.'}
          {level === 3 && 'You have reached the highest level. Keep practicing to maintain your knowledge!'}
        </p>
      )}
    </div>
  )
}
