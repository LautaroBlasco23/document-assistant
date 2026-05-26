import * as React from 'react'
import { BookMarked, Sparkles } from 'lucide-react'
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

export function StudyTab({ treeId, selectedChapter, chapters }: StudyTabProps) {
  const [studyActive, setStudyActive] = React.useState(false)

  const store = useKnowledgeTreeStore()

  const chapterKey = selectedChapter !== null ? questionKey(treeId, selectedChapter) : null
  const questionsByType = chapterKey ? (store.questionsByType[chapterKey] ?? {}) : {}
  const flashcards = chapterKey ? (store.flashcardsByChapter[chapterKey] ?? []) : []

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

  React.useEffect(() => {
    if (treeId && selectedChapter !== null) {
      void store.fetchQuestions(treeId, selectedChapter)
      void store.fetchFlashcards(treeId, selectedChapter)
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
        onFinish={() => setStudyActive(false)}
      />
    )
  }

  return (
    <StudyReady
      typeCounts={typeCounts}
      totalCount={allQuestions.length}
      onStart={() => setStudyActive(true)}
    />
  )
}
