import * as React from 'react'
import { BookMarked, Sparkles, Clock, BookOpen, ArrowRight } from 'lucide-react'
import { StudyReady } from './study-ready'
import { StudySession } from './study-session'
import { useKnowledgeTreeStore, questionKey } from '../../stores/knowledge-tree-store'
import type {
  KnowledgeChapter,
  ExamQuestion,
  TrueFalseQuestion,
  MultipleChoiceQuestion,
  MatchingQuestion,
  CheckboxQuestion,
  FlashcardQuestion,
} from '../../types/knowledge-tree'

interface StudyTabProps {
  treeId: string
  selectedChapter: number | null
  chapters: KnowledgeChapter[]
}

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

export function StudyTab({ treeId, selectedChapter, chapters }: StudyTabProps) {
  const [studyActive, setStudyActive] = React.useState(false)

  const store = useKnowledgeTreeStore()

  const chapterKey = selectedChapter !== null ? questionKey(treeId, selectedChapter) : null
  const questionsByType = chapterKey ? (store.questionsByType[chapterKey] ?? {}) : {}
  const flashcards = chapterKey ? (store.flashcardsByChapter[chapterKey] ?? []) : []
  const studySessions = chapterKey ? (store.studySessionsByChapter[chapterKey] ?? []) : []

  const tfQuestions = (questionsByType['true_false'] ?? []) as TrueFalseQuestion[]
  const mcQuestions = (questionsByType['multiple_choice'] ?? []) as MultipleChoiceQuestion[]
  const matchingQuestions = (questionsByType['matching'] ?? []) as MatchingQuestion[]
  const cbQuestions = (questionsByType['checkbox'] ?? []) as CheckboxQuestion[]

  const flashcardQuestions: FlashcardQuestion[] = flashcards.map((f) => ({
    type: 'flashcard' as const,
    id: f.id,
    front: f.front,
    back: f.back,
  }))

  const allQuestions: ExamQuestion[] = selectedChapter !== null
    ? [...tfQuestions, ...mcQuestions, ...matchingQuestions, ...cbQuestions, ...flashcardQuestions]
    : []

  const typeCounts = selectedChapter !== null
    ? [
        { label: 'True / False', count: tfQuestions.length },
        { label: 'Multiple Choice', count: mcQuestions.length },
        { label: 'Matching', count: matchingQuestions.length },
        { label: 'Checkbox', count: cbQuestions.length },
        { label: 'Flashcards', count: flashcardQuestions.length },
      ]
    : []

  const handleSaveSession = (results: { total_cards: number; question_ids: string[] }) => {
    if (selectedChapter !== null) {
      void store.saveStudySession(treeId, selectedChapter, results)
    }
  }

  const handleFinishStudy = () => {
    setStudyActive(false)
    if (selectedChapter !== null) {
      void store.fetchStudySessions(treeId, selectedChapter)
    }
  }

  React.useEffect(() => {
    if (treeId && selectedChapter !== null) {
      void store.fetchQuestions(treeId, selectedChapter)
      void store.fetchFlashcards(treeId, selectedChapter)
      void store.fetchStudySessions(treeId, selectedChapter)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [treeId, selectedChapter])

  if (chapters.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <Sparkles className="h-10 w-10 text-text-tertiary mb-4" />
        <p className="text-sm font-medium text-gray-500">No chapters yet</p>
        <p className="text-xs text-text-tertiary mt-1">
          Add chapters in the Knowledge Documents tab, then come back here to study.
        </p>
      </div>
    )
  }

  if (selectedChapter === null) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
        <BookMarked className="h-10 w-10 text-gray-200" />
        <p className="text-sm font-medium text-gray-500">Select a chapter</p>
        <p className="text-xs text-gray-400">Choose a chapter from the sidebar to start studying.</p>
      </div>
    )
  }

  if (studyActive) {
    return (
      <StudySession
        questions={allQuestions}
        onFinish={handleFinishStudy}
        onSave={handleSaveSession}
      />
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <StudyReady
        typeCounts={typeCounts}
        totalCount={allQuestions.length}
        onStart={() => setStudyActive(true)}
      />

      {/* Study history */}
      {studySessions.length > 0 && (
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-gray-400" />
            <span className="text-sm font-medium text-text-primary">Study History</span>
          </div>

          <div className="flex flex-col gap-2">
            {studySessions.map((session) => (
              <div
                key={session.id}
                className="flex items-center gap-4 rounded-lg border border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 px-4 py-3 text-left"
              >
                <BookOpen className="h-5 w-5 shrink-0 text-blue-400" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-text-primary">
                      Studied {session.total_cards} {session.total_cards === 1 ? 'card' : 'cards'}
                    </span>
                  </div>
                  <p className="text-xs text-text-tertiary mt-0.5">{formatDate(session.created_at)}</p>
                </div>
                <ArrowRight className="h-4 w-4 shrink-0 text-gray-300" />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
