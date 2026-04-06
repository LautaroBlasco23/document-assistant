import * as React from 'react'
import { Sparkles, BookOpen, Zap, ChevronDown, ChevronUp, GraduationCap } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Badge } from '../../components/ui/badge'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs'
import { ExamSession } from '../document/exam-session'
import { useExamStore } from '../../stores/exam-store'
import { mockFlashcards } from '../../mocks/flashcards'
import type { KnowledgeChapter } from '../../types/knowledge-tree'

interface ContentTabProps {
  treeId: string
  selectedChapter: number
  chapters: KnowledgeChapter[]
  onChapterChange: (chapter: number) => void
}

type GenerateStatus = 'idle' | 'loading' | 'done'

const MOCK_SUMMARY = `This chapter covers the foundational concepts and key principles that underpin the topic. The main areas explored include the theoretical basis, practical applications, and common pitfalls to avoid.

Key takeaways:
• The core principle drives all other concepts in this domain
• Understanding the trade-offs between different approaches is critical
• Practical implementation requires adapting theory to real-world constraints
• Regular review and iteration leads to mastery`

const MOCK_FLASHCARD_LIST = [
  { front: 'What is the core principle of this topic?', back: 'The fundamental idea that drives all related concepts and provides the theoretical foundation for practical applications.' },
  { front: 'What are the main trade-offs to consider?', back: 'Speed vs. accuracy, simplicity vs. flexibility, and short-term vs. long-term maintainability.' },
  { front: 'How does theory translate to practice?', back: 'By adapting core principles to the specific constraints and requirements of the real-world environment, iterating based on feedback.' },
  { front: 'What is the most common pitfall?', back: 'Over-engineering: adding unnecessary complexity before validating the simpler solution works.' },
]

// Use the first available mock flashcard set for the exam
const EXAM_CARDS = Object.values(mockFlashcards)[0] ?? []

export function ContentTab({ treeId, selectedChapter, chapters, onChapterChange }: ContentTabProps) {
  const [summaryStatus, setSummaryStatus] = React.useState<GenerateStatus>('idle')
  const [flashcardsStatus, setFlashcardsStatus] = React.useState<GenerateStatus>('idle')
  const [expandedCard, setExpandedCard] = React.useState<number | null>(null)
  const [activeSubTab, setActiveSubTab] = React.useState<'summary' | 'flashcards' | 'exam'>('summary')

  const activeExam = useExamStore((state) => state.activeExam)
  const startExam = useExamStore((state) => state.startExam)

  const currentChapter = chapters.find((c) => c.number === selectedChapter)

  const handleGenerateSummary = async () => {
    setSummaryStatus('loading')
    await new Promise<void>((resolve) => setTimeout(resolve, 2000))
    setSummaryStatus('done')
  }

  const handleGenerateFlashcards = async () => {
    setFlashcardsStatus('loading')
    await new Promise<void>((resolve) => setTimeout(resolve, 2500))
    setFlashcardsStatus('done')
  }

  const handleChapterReset = () => {
    setSummaryStatus('idle')
    setFlashcardsStatus('idle')
    setExpandedCard(null)
  }

  const isExamActive = activeExam?.docHash === treeId && activeExam?.chapter === selectedChapter

  return (
    <div className="flex flex-col gap-5">
      {/* Chapter selector */}
      <div className="flex flex-col gap-1.5">
        <label className="text-xs font-medium text-gray-500">Chapter</label>
        <select
          value={selectedChapter}
          onChange={(e) => { onChapterChange(Number(e.target.value)); handleChapterReset() }}
          className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        >
          {chapters.map((ch) => (
            <option key={ch.number} value={ch.number}>
              {ch.title}
            </option>
          ))}
        </select>
      </div>

      {chapters.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <Sparkles className="h-10 w-10 text-gray-200 mb-4" />
          <p className="text-sm font-medium text-gray-500">No chapters yet</p>
          <p className="text-xs text-gray-400 mt-1">
            Add chapters in the Knowledge Documents tab, then come back here to generate content.
          </p>
        </div>
      ) : (
        <>
          <p className="text-xs text-gray-500">
            Content is generated from the knowledge documents in{' '}
            <span className="font-medium text-gray-700">{currentChapter?.title}</span>.
            Make sure you've added documents in the Knowledge Documents tab first.
          </p>

          {/* Sub-tabs */}
          <Tabs value={activeSubTab} onValueChange={(v) => setActiveSubTab(v as typeof activeSubTab)}>
            <TabsList>
              <TabsTrigger value="summary">
                <BookOpen className="h-3.5 w-3.5 mr-1.5 inline-block" />
                Summary
              </TabsTrigger>
              <TabsTrigger value="flashcards">
                <Zap className="h-3.5 w-3.5 mr-1.5 inline-block" />
                Flashcards
              </TabsTrigger>
              <TabsTrigger value="exam">
                <GraduationCap className="h-3.5 w-3.5 mr-1.5 inline-block" />
                Exam
              </TabsTrigger>
            </TabsList>

            {/* Summary sub-tab */}
            <TabsContent value="summary">
              <div className="flex flex-col gap-3">
                {summaryStatus === 'idle' && (
                  <>
                    <p className="text-sm text-gray-500">
                      A structured summary of this chapter based on its knowledge documents.
                    </p>
                    <Button variant="secondary" size="sm" onClick={() => void handleGenerateSummary()} className="self-start">
                      <Sparkles className="h-3.5 w-3.5 mr-1" />
                      Generate Summary
                    </Button>
                  </>
                )}
                {summaryStatus === 'loading' && (
                  <div className="flex items-center gap-2 text-sm text-gray-400 py-4">
                    <div className="h-4 w-4 rounded-full border-2 border-primary border-t-transparent animate-spin" />
                    Generating from knowledge documents...
                  </div>
                )}
                {summaryStatus === 'done' && (
                  <>
                    <div className="flex items-center gap-2">
                      <Badge variant="success">Generated</Badge>
                    </div>
                    <div className="bg-gray-50 rounded-md p-4 text-sm text-gray-700 leading-relaxed whitespace-pre-line border border-gray-200">
                      {MOCK_SUMMARY}
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => setSummaryStatus('idle')} className="self-start text-gray-400">
                      Regenerate
                    </Button>
                  </>
                )}
              </div>
            </TabsContent>

            {/* Flashcards sub-tab */}
            <TabsContent value="flashcards">
              <div className="flex flex-col gap-3">
                {flashcardsStatus === 'idle' && (
                  <>
                    <p className="text-sm text-gray-500">
                      Q&A flashcards extracted from key concepts in this chapter's documents.
                    </p>
                    <Button variant="secondary" size="sm" onClick={() => void handleGenerateFlashcards()} className="self-start">
                      <Sparkles className="h-3.5 w-3.5 mr-1" />
                      Generate Flashcards
                    </Button>
                  </>
                )}
                {flashcardsStatus === 'loading' && (
                  <div className="flex items-center gap-2 text-sm text-gray-400 py-4">
                    <div className="h-4 w-4 rounded-full border-2 border-yellow-400 border-t-transparent animate-spin" />
                    Extracting concepts...
                  </div>
                )}
                {flashcardsStatus === 'done' && (
                  <>
                    <div className="flex items-center gap-2">
                      <Badge variant="success">{MOCK_FLASHCARD_LIST.length} cards</Badge>
                    </div>
                    <div className="flex flex-col gap-2">
                      {MOCK_FLASHCARD_LIST.map((card, i) => (
                        <div
                          key={i}
                          className="border border-gray-200 rounded-md overflow-hidden cursor-pointer"
                          onClick={() => setExpandedCard(expandedCard === i ? null : i)}
                        >
                          <div className="flex items-center justify-between px-3 py-2 bg-white hover:bg-gray-50">
                            <span className="text-sm font-medium text-gray-700 flex-1 pr-2">{card.front}</span>
                            {expandedCard === i ? (
                              <ChevronUp className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                            ) : (
                              <ChevronDown className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                            )}
                          </div>
                          {expandedCard === i && (
                            <div className="px-3 py-2 bg-blue-50 border-t border-gray-200">
                              <p className="text-sm text-gray-600">{card.back}</p>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => setFlashcardsStatus('idle')} className="self-start text-gray-400">
                      Regenerate
                    </Button>
                  </>
                )}
              </div>
            </TabsContent>

            {/* Exam sub-tab */}
            <TabsContent value="exam">
              {isExamActive ? (
                <ExamSession />
              ) : (
                <KnowledgeExamReady
                  treeId={treeId}
                  chapter={selectedChapter}
                  onStart={() => startExam(treeId, selectedChapter, EXAM_CARDS)}
                />
              )}
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  )
}

interface KnowledgeExamReadyProps {
  treeId: string
  chapter: number
  onStart: () => void
}

function KnowledgeExamReady({ treeId: _treeId, chapter: _chapter, onStart }: KnowledgeExamReadyProps) {
  if (EXAM_CARDS.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <GraduationCap className="h-8 w-8 text-gray-300 mb-3" />
        <p className="text-sm font-medium text-gray-500">No flashcards available</p>
        <p className="text-xs text-gray-400 mt-1">
          Generate flashcards first from the Flashcards tab to take an exam.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 flex flex-col gap-3">
        <p className="text-sm text-gray-600">
          This exam has <span className="font-semibold text-gray-800">{EXAM_CARDS.length}</span>{' '}
          {EXAM_CARDS.length === 1 ? 'question' : 'questions'}. You must answer all correctly to pass.
        </p>
        <Button variant="primary" size="sm" onClick={onStart} className="self-start">
          Start Exam
        </Button>
      </div>
    </div>
  )
}
