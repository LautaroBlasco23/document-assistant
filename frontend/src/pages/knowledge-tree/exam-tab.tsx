import * as React from 'react'
import { BookMarked, Sparkles, Clock, Trophy, ArrowRight } from 'lucide-react'
import { Badge } from '../../components/ui/badge'
import { KnowledgeExamSession } from './knowledge-exam-session'
import { KnowledgeExamReady } from './knowledge-exam-ready'
import { ExamReview } from './exam-review'
import { useKnowledgeTreeStore } from '../../stores/knowledge-tree-store'
import { questionKey } from '../../stores/knowledge-tree-store'
import type {
  KnowledgeChapter,
  ExamQuestion,
  ExamSession,
  TrueFalseQuestion,
  MultipleChoiceQuestion,
  MatchingQuestion,
  CheckboxQuestion,
} from '../../types/knowledge-tree'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ExamTabProps {
  treeId: string
  selectedChapter: number | null
  chapters: KnowledgeChapter[]
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function scoreColor(score: number): string {
  if (score >= 80) return 'text-green-600'
  if (score >= 50) return 'text-amber-600'
  return 'text-red-600'
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ExamTab({ treeId, selectedChapter, chapters }: ExamTabProps) {
  const [examActive, setExamActive] = React.useState(false)
  const [reviewSession, setReviewSession] = React.useState<ExamSession | null>(null)

  const store = useKnowledgeTreeStore()

  const chapterKey = selectedChapter !== null ? questionKey(treeId, selectedChapter) : null
  const questionsByType = chapterKey ? (store.questionsByType[chapterKey] ?? {}) : {}
  const examSessions = chapterKey ? (store.examSessionsByChapter[chapterKey] ?? []) : []

  const tfQuestions = (questionsByType['true_false'] ?? []) as TrueFalseQuestion[]
  const mcQuestions = (questionsByType['multiple_choice'] ?? []) as MultipleChoiceQuestion[]
  const matchingQuestions = (questionsByType['matching'] ?? []) as MatchingQuestion[]
  const cbQuestions = (questionsByType['checkbox'] ?? []) as CheckboxQuestion[]

  const examQuestions: ExamQuestion[] = selectedChapter !== null
    ? [...tfQuestions, ...mcQuestions, ...matchingQuestions, ...cbQuestions]
    : []

  const typeCounts = selectedChapter !== null
    ? [
        { label: 'True / False', count: tfQuestions.length },
        { label: 'Multiple Choice', count: mcQuestions.length },
        { label: 'Matching', count: matchingQuestions.length },
        { label: 'Checkbox', count: cbQuestions.length },
      ]
    : []

  // Load questions and exam sessions when chapter is selected
  React.useEffect(() => {
    if (treeId && selectedChapter !== null) {
      void store.fetchQuestions(treeId, selectedChapter)
      void store.fetchExamSessions(treeId, selectedChapter)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [treeId, selectedChapter])

  const handleSaveExam = (results: { score: number; total_questions: number; correct_count: number; question_ids: string[]; results: Record<string, boolean> }) => {
    if (selectedChapter !== null) {
      void store.saveExamSession(treeId, selectedChapter, results)
    }
  }

  // Review mode: load full session data
  const handleReviewSession = async (session: ExamSession) => {
    try {
      // Use the already-loaded session data from the list
      setReviewSession(session)
    } catch {
      // Session not found
    }
  }

  const handleFinishExam = () => {
    setExamActive(false)
    if (selectedChapter !== null) {
      void store.fetchExamSessions(treeId, selectedChapter)
    }
  }

  if (chapters.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <Sparkles className="h-10 w-10 text-gray-200 mb-4" />
        <p className="text-sm font-medium text-gray-500">No chapters yet</p>
        <p className="text-xs text-gray-400 mt-1">
          Add chapters in the Knowledge Documents tab, then come back here to take exams.
        </p>
      </div>
    )
  }

  if (selectedChapter === null) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
        <BookMarked className="h-10 w-10 text-gray-200" />
        <p className="text-sm font-medium text-gray-500">Select a chapter</p>
        <p className="text-xs text-gray-400">Choose a chapter from the sidebar to take an exam.</p>
      </div>
    )
  }

  // Review mode
  if (reviewSession) {
    return (
      <div className="flex flex-col gap-4">
        <button
          onClick={() => setReviewSession(null)}
          className="text-sm text-primary hover:underline self-start"
        >
          ← Back to exams
        </button>
        <ExamReview session={reviewSession} allQuestions={examQuestions} />
      </div>
    )
  }

  // Active exam
  if (examActive) {
    return (
      <KnowledgeExamSession
        questions={examQuestions}
        onFinish={handleFinishExam}
        onSave={handleSaveExam}
      />
    )
  }

  // Main view: history + start button
  return (
    <div className="flex flex-col gap-6">
      {/* Start new exam section */}
      <KnowledgeExamReady
        typeCounts={typeCounts}
        totalCount={examQuestions.length}
        onStart={() => setExamActive(true)}
      />

      {/* Exam history */}
      {examSessions.length > 0 && (
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-gray-400" />
            <span className="text-sm font-medium text-gray-700">Exam History</span>
          </div>

          <div className="flex flex-col gap-2">
            {examSessions.map((session) => (
              <button
                key={session.id}
                onClick={() => void handleReviewSession(session)}
                className="flex items-center gap-4 rounded-lg border border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 px-4 py-3 hover:border-primary/30 transition-colors text-left"
              >
                <Trophy className="h-5 w-5 shrink-0 text-amber-400" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`font-semibold text-sm ${scoreColor(session.score)}`}>
                      {Math.round(session.score)}%
                    </span>
                    <Badge variant="neutral" className="text-xs py-0">
                      {session.correct_count}/{session.total_questions} correct
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5">{formatDate(session.created_at)}</p>
                </div>
                <ArrowRight className="h-4 w-4 shrink-0 text-gray-300" />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
