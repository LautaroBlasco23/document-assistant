import * as React from 'react'
import {
  Sparkles,
  BookOpen,
  Zap,
  ChevronDown,
  ChevronUp,
  GraduationCap,
  ToggleLeft,
  ListChecks,
  Link2,
  CheckSquare,
  Check,
  RefreshCw,
} from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Badge } from '../../components/ui/badge'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs'
import { KnowledgeExamSession } from './knowledge-exam-session'
import { mockExamQuestions } from '../../mocks/knowledge-exam'
import type {
  KnowledgeChapter,
  TrueFalseQuestion,
  MultipleChoiceQuestion,
  MatchingQuestion,
  CheckboxQuestion,
  FlashcardQuestion,
  ExamQuestion,
} from '../../types/knowledge-tree'

// ---------------------------------------------------------------------------
// Mock generation helpers — filters the shared mock data by type
// ---------------------------------------------------------------------------

const MOCK_TF = mockExamQuestions.filter(
  (q): q is TrueFalseQuestion => q.type === 'true-false',
)
const MOCK_MC = mockExamQuestions.filter(
  (q): q is MultipleChoiceQuestion => q.type === 'multiple-choice',
)
const MOCK_MATCHING = mockExamQuestions.filter(
  (q): q is MatchingQuestion => q.type === 'matching',
)
const MOCK_CB = mockExamQuestions.filter(
  (q): q is CheckboxQuestion => q.type === 'checkbox',
)

const MOCK_SUMMARY = `This chapter covers the foundational concepts and key principles that underpin the topic. The main areas explored include the theoretical basis, practical applications, and common pitfalls to avoid.

Key takeaways:
• The core principle drives all other concepts in this domain
• Understanding the trade-offs between different approaches is critical
• Practical implementation requires adapting theory to real-world constraints
• Regular review and iteration leads to mastery`

const MOCK_FLASHCARD_LIST: FlashcardQuestion[] = [
  {
    type: 'flashcard',
    id: 'fc-gen-1',
    front: 'What is the core principle of this topic?',
    back: 'The fundamental idea that drives all related concepts and provides the theoretical foundation for practical applications.',
  },
  {
    type: 'flashcard',
    id: 'fc-gen-2',
    front: 'What are the main trade-offs to consider?',
    back: 'Speed vs. accuracy, simplicity vs. flexibility, and short-term vs. long-term maintainability.',
  },
  {
    type: 'flashcard',
    id: 'fc-gen-3',
    front: 'How does theory translate to practice?',
    back: 'By adapting core principles to the specific constraints and requirements of the real-world environment, iterating based on feedback.',
  },
  {
    type: 'flashcard',
    id: 'fc-gen-4',
    front: 'What is the most common pitfall?',
    back: 'Over-engineering: adding unnecessary complexity before validating the simpler solution works.',
  },
]

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type GenerateStatus = 'idle' | 'loading' | 'done'
type SubTab = 'summary' | 'flashcards' | 'questions' | 'exam'

interface ContentTabProps {
  treeId: string
  selectedChapter: number
  chapters: KnowledgeChapter[]
  onChapterChange: (chapter: number) => void
}

// ---------------------------------------------------------------------------
// Shared generator section shell
// ---------------------------------------------------------------------------

interface GeneratorSectionProps {
  icon: React.ReactNode
  title: string
  description: string
  status: GenerateStatus
  count: number
  spinnerColor?: string
  onGenerate: () => void
  children: React.ReactNode // rendered when status === 'done'
}

function GeneratorSection({
  icon,
  title,
  description,
  status,
  count,
  spinnerColor = 'border-primary',
  onGenerate,
  children,
}: GeneratorSectionProps) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-gray-50">
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-sm font-medium text-gray-700">{title}</span>
          {status === 'done' && (
            <Badge variant="success" className="text-xs py-0">
              {count} {count === 1 ? 'question' : 'questions'}
            </Badge>
          )}
        </div>
        {status !== 'loading' && (
          <Button
            variant={status === 'done' ? 'ghost' : 'secondary'}
            size="sm"
            onClick={onGenerate}
            className={status === 'done' ? 'text-gray-400 h-7 px-2' : 'h-7'}
          >
            {status === 'done' ? (
              <>
                <RefreshCw className="h-3 w-3 mr-1" />
                Regenerate
              </>
            ) : (
              <>
                <Sparkles className="h-3.5 w-3.5 mr-1" />
                Generate
              </>
            )}
          </Button>
        )}
      </div>

      {/* Body */}
      <div className="px-4 py-3">
        {status === 'idle' && (
          <p className="text-xs text-gray-400">{description}</p>
        )}
        {status === 'loading' && (
          <div className="flex items-center gap-2 text-xs text-gray-400 py-1">
            <div
              className={`h-3.5 w-3.5 rounded-full border-2 ${spinnerColor} border-t-transparent animate-spin`}
            />
            Generating from knowledge documents...
          </div>
        )}
        {status === 'done' && children}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Question preview lists
// ---------------------------------------------------------------------------

function TrueFalseList({ questions }: { questions: TrueFalseQuestion[] }) {
  return (
    <ul className="flex flex-col gap-1.5">
      {questions.map((q) => (
        <li
          key={q.id}
          className="flex items-start gap-2 rounded-md border border-gray-100 bg-gray-50 px-3 py-2 text-xs"
        >
          <span
            className={`mt-0.5 shrink-0 rounded px-1 py-0.5 font-semibold uppercase text-[10px] ${
              q.answer
                ? 'bg-green-100 text-green-700'
                : 'bg-red-100 text-red-600'
            }`}
          >
            {q.answer ? 'True' : 'False'}
          </span>
          <span className="text-gray-700 leading-relaxed">{q.statement}</span>
        </li>
      ))}
    </ul>
  )
}

function MultipleChoiceList({ questions }: { questions: MultipleChoiceQuestion[] }) {
  return (
    <ul className="flex flex-col gap-2">
      {questions.map((q) => (
        <li
          key={q.id}
          className="rounded-md border border-gray-100 bg-gray-50 px-3 py-2"
        >
          <p className="text-xs font-medium text-gray-700 mb-1.5">{q.question}</p>
          <ul className="flex flex-col gap-0.5">
            {q.choices.map((choice, i) => (
              <li
                key={i}
                className={`flex items-center gap-1.5 text-xs rounded px-1.5 py-0.5 ${
                  i === q.correctIndex
                    ? 'text-green-700 bg-green-50'
                    : 'text-gray-500'
                }`}
              >
                {i === q.correctIndex ? (
                  <Check className="h-3 w-3 shrink-0 text-green-500" strokeWidth={3} />
                ) : (
                  <span className="h-3 w-3 shrink-0" />
                )}
                <span>{String.fromCharCode(65 + i)}. {choice}</span>
              </li>
            ))}
          </ul>
        </li>
      ))}
    </ul>
  )
}

function MatchingList({ questions }: { questions: MatchingQuestion[] }) {
  return (
    <ul className="flex flex-col gap-2">
      {questions.map((q) => (
        <li key={q.id} className="rounded-md border border-gray-100 bg-gray-50 px-3 py-2">
          <p className="text-xs font-medium text-gray-600 mb-1.5">{q.prompt}</p>
          <table className="w-full text-xs border-collapse">
            <tbody>
              {q.pairs.map((pair, i) => (
                <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  <td className="rounded-l px-2 py-1 font-medium text-gray-700 w-36 align-top border border-gray-100">
                    {pair.term}
                  </td>
                  <td className="rounded-r px-2 py-1 text-gray-500 align-top border border-gray-100">
                    {pair.definition}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </li>
      ))}
    </ul>
  )
}

function CheckboxList({ questions }: { questions: CheckboxQuestion[] }) {
  return (
    <ul className="flex flex-col gap-2">
      {questions.map((q) => (
        <li key={q.id} className="rounded-md border border-gray-100 bg-gray-50 px-3 py-2">
          <p className="text-xs font-medium text-gray-700 mb-1.5">{q.question}</p>
          <ul className="flex flex-col gap-0.5">
            {q.choices.map((choice, i) => {
              const correct = q.correctIndices.includes(i)
              return (
                <li
                  key={i}
                  className={`flex items-center gap-1.5 text-xs rounded px-1.5 py-0.5 ${
                    correct ? 'text-green-700 bg-green-50' : 'text-gray-500'
                  }`}
                >
                  <span
                    className={`h-3 w-3 shrink-0 rounded border flex items-center justify-center ${
                      correct ? 'border-green-500 bg-green-500' : 'border-gray-300'
                    }`}
                  >
                    {correct && <Check className="h-2 w-2 text-white" strokeWidth={3} />}
                  </span>
                  {choice}
                </li>
              )
            })}
          </ul>
        </li>
      ))}
    </ul>
  )
}

// ---------------------------------------------------------------------------
// Exam ready screen
// ---------------------------------------------------------------------------

interface ExamTypeCount {
  label: string
  count: number
}

interface KnowledgeExamReadyProps {
  typeCounts: ExamTypeCount[]
  totalCount: number
  onStart: () => void
}

function KnowledgeExamReady({ typeCounts, totalCount, onStart }: KnowledgeExamReadyProps) {
  const hasQuestions = totalCount > 0

  if (!hasQuestions) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center gap-3">
        <GraduationCap className="h-9 w-9 text-gray-200" />
        <div>
          <p className="text-sm font-medium text-gray-500">No questions generated yet</p>
          <p className="text-xs text-gray-400 mt-1">
            Go to the <span className="font-medium text-gray-600">Questions</span> tab and generate
            at least one question type to take an exam.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 flex flex-col gap-3">
        <p className="text-sm text-gray-600">
          Ready to start with{' '}
          <span className="font-semibold text-gray-800">{totalCount}</span>{' '}
          {totalCount === 1 ? 'question' : 'questions'} from the following types:
        </p>

        <div className="flex flex-col gap-1">
          {typeCounts
            .filter((t) => t.count > 0)
            .map((t) => (
              <div key={t.label} className="flex items-center justify-between text-xs">
                <span className="text-gray-600">{t.label}</span>
                <span className="font-medium text-gray-700">
                  {t.count} {t.count === 1 ? 'question' : 'questions'}
                </span>
              </div>
            ))}
        </div>

        <Button variant="primary" size="sm" onClick={onStart} className="self-start mt-1">
          Start Exam
        </Button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main content tab
// ---------------------------------------------------------------------------

export function ContentTab({ treeId: _treeId, selectedChapter, chapters, onChapterChange }: ContentTabProps) {
  const [activeSubTab, setActiveSubTab] = React.useState<SubTab>('summary')

  // Summary
  const [summaryStatus, setSummaryStatus] = React.useState<GenerateStatus>('idle')

  // Flashcards
  const [flashcardsStatus, setFlashcardsStatus] = React.useState<GenerateStatus>('idle')
  const [flashcardQuestions, setFlashcardQuestions] = React.useState<FlashcardQuestion[]>([])
  const [expandedCard, setExpandedCard] = React.useState<number | null>(null)

  // Question types
  const [tfStatus, setTfStatus] = React.useState<GenerateStatus>('idle')
  const [tfQuestions, setTfQuestions] = React.useState<TrueFalseQuestion[]>([])

  const [mcStatus, setMcStatus] = React.useState<GenerateStatus>('idle')
  const [mcQuestions, setMcQuestions] = React.useState<MultipleChoiceQuestion[]>([])

  const [matchingStatus, setMatchingStatus] = React.useState<GenerateStatus>('idle')
  const [matchingQuestions, setMatchingQuestions] = React.useState<MatchingQuestion[]>([])

  const [cbStatus, setCbStatus] = React.useState<GenerateStatus>('idle')
  const [cbQuestions, setCbQuestions] = React.useState<CheckboxQuestion[]>([])

  // Exam
  const [examActive, setExamActive] = React.useState(false)

  const currentChapter = chapters.find((c) => c.number === selectedChapter)

  // Combined exam questions from all generated types
  const examQuestions: ExamQuestion[] = [
    ...tfQuestions,
    ...mcQuestions,
    ...matchingQuestions,
    ...cbQuestions,
    ...flashcardQuestions,
  ]

  const typeCounts: ExamTypeCount[] = [
    { label: 'True / False', count: tfQuestions.length },
    { label: 'Multiple Choice', count: mcQuestions.length },
    { label: 'Matching', count: matchingQuestions.length },
    { label: 'Checkbox', count: cbQuestions.length },
    { label: 'Flashcards', count: flashcardQuestions.length },
  ]

  // -- generators (mock: simulate async generation) --

  const generate = async <T,>(
    setter: React.Dispatch<React.SetStateAction<GenerateStatus>>,
    dataSetter: React.Dispatch<React.SetStateAction<T[]>>,
    data: T[],
    delay = 2000,
  ) => {
    setter('loading')
    await new Promise<void>((resolve) => setTimeout(resolve, delay))
    dataSetter(data)
    setter('done')
  }

  const handleGenerateTF = () =>
    void generate(setTfStatus, setTfQuestions, MOCK_TF)
  const handleGenerateMC = () =>
    void generate(setMcStatus, setMcQuestions, MOCK_MC, 2200)
  const handleGenerateMatching = () =>
    void generate(setMatchingStatus, setMatchingQuestions, MOCK_MATCHING, 2400)
  const handleGenerateCB = () =>
    void generate(setCbStatus, setCbQuestions, MOCK_CB, 2100)
  const handleGenerateSummary = async () => {
    setSummaryStatus('loading')
    await new Promise<void>((resolve) => setTimeout(resolve, 2000))
    setSummaryStatus('done')
  }
  const handleGenerateFlashcards = () =>
    void generate(setFlashcardsStatus, setFlashcardQuestions, MOCK_FLASHCARD_LIST, 2500)

  const handleChapterReset = () => {
    setSummaryStatus('idle')
    setFlashcardsStatus('idle')
    setExpandedCard(null)
    setTfStatus('idle'); setTfQuestions([])
    setMcStatus('idle'); setMcQuestions([])
    setMatchingStatus('idle'); setMatchingQuestions([])
    setCbStatus('idle'); setCbQuestions([])
    setFlashcardQuestions([])
    setExamActive(false)
  }

  return (
    <div className="flex flex-col gap-5">
      {/* Chapter selector */}
      <div className="flex flex-col gap-1.5">
        <label className="text-xs font-medium text-gray-500">Chapter</label>
        <select
          value={selectedChapter}
          onChange={(e) => {
            onChapterChange(Number(e.target.value))
            handleChapterReset()
          }}
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
            Make sure you&apos;ve added documents in the Knowledge Documents tab first.
          </p>

          <Tabs value={activeSubTab} onValueChange={(v) => setActiveSubTab(v as SubTab)}>
            <TabsList>
              <TabsTrigger value="summary">
                <BookOpen className="h-3.5 w-3.5 mr-1.5 inline-block" />
                Summary
              </TabsTrigger>
              <TabsTrigger value="flashcards">
                <Zap className="h-3.5 w-3.5 mr-1.5 inline-block" />
                Flashcards
              </TabsTrigger>
              <TabsTrigger value="questions">
                <ListChecks className="h-3.5 w-3.5 mr-1.5 inline-block" />
                Questions
              </TabsTrigger>
              <TabsTrigger value="exam">
                <GraduationCap className="h-3.5 w-3.5 mr-1.5 inline-block" />
                Exam
              </TabsTrigger>
            </TabsList>

            {/* Summary */}
            <TabsContent value="summary">
              <div className="flex flex-col gap-3">
                {summaryStatus === 'idle' && (
                  <>
                    <p className="text-sm text-gray-500">
                      A structured summary of this chapter based on its knowledge documents.
                    </p>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handleGenerateSummary}
                      className="self-start"
                    >
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
                    <Badge variant="success">Generated</Badge>
                    <div className="bg-gray-50 rounded-md p-4 text-sm text-gray-700 leading-relaxed whitespace-pre-line border border-gray-200">
                      {MOCK_SUMMARY}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSummaryStatus('idle')}
                      className="self-start text-gray-400"
                    >
                      Regenerate
                    </Button>
                  </>
                )}
              </div>
            </TabsContent>

            {/* Flashcards */}
            <TabsContent value="flashcards">
              <div className="flex flex-col gap-3">
                {flashcardsStatus === 'idle' && (
                  <>
                    <p className="text-sm text-gray-500">
                      Q&amp;A flashcards extracted from key concepts in this chapter&apos;s documents.
                    </p>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handleGenerateFlashcards}
                      className="self-start"
                    >
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
                    <Badge variant="success">{flashcardQuestions.length} cards</Badge>
                    <div className="flex flex-col gap-2">
                      {flashcardQuestions.map((card, i) => (
                        <div
                          key={card.id}
                          className="border border-gray-200 rounded-md overflow-hidden cursor-pointer"
                          onClick={() => setExpandedCard(expandedCard === i ? null : i)}
                        >
                          <div className="flex items-center justify-between px-3 py-2 bg-white hover:bg-gray-50">
                            <span className="text-sm font-medium text-gray-700 flex-1 pr-2">
                              {card.front}
                            </span>
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
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => { setFlashcardsStatus('idle'); setFlashcardQuestions([]) }}
                      className="self-start text-gray-400"
                    >
                      Regenerate
                    </Button>
                  </>
                )}
              </div>
            </TabsContent>

            {/* Questions */}
            <TabsContent value="questions">
              <div className="flex flex-col gap-4">
                <p className="text-xs text-gray-400">
                  Generate each question type independently. All generated questions will be
                  available in the Exam tab.
                </p>

                <GeneratorSection
                  icon={<ToggleLeft className="h-4 w-4 text-indigo-400" />}
                  title="True / False"
                  description="Statements the student must evaluate as true or false, with explanations."
                  status={tfStatus}
                  count={tfQuestions.length}
                  spinnerColor="border-indigo-400"
                  onGenerate={handleGenerateTF}
                >
                  <TrueFalseList questions={tfQuestions} />
                </GeneratorSection>

                <GeneratorSection
                  icon={<ListChecks className="h-4 w-4 text-violet-400" />}
                  title="Multiple Choice"
                  description="Questions with four options where only one is correct."
                  status={mcStatus}
                  count={mcQuestions.length}
                  spinnerColor="border-violet-400"
                  onGenerate={handleGenerateMC}
                >
                  <MultipleChoiceList questions={mcQuestions} />
                </GeneratorSection>

                <GeneratorSection
                  icon={<Link2 className="h-4 w-4 text-amber-400" />}
                  title="Matching"
                  description="Term-to-definition pairs the student must connect correctly."
                  status={matchingStatus}
                  count={matchingQuestions.length}
                  spinnerColor="border-amber-400"
                  onGenerate={handleGenerateMatching}
                >
                  <MatchingList questions={matchingQuestions} />
                </GeneratorSection>

                <GeneratorSection
                  icon={<CheckSquare className="h-4 w-4 text-teal-400" />}
                  title="Checkbox (Select All That Apply)"
                  description="Questions where multiple answers may be correct."
                  status={cbStatus}
                  count={cbQuestions.length}
                  spinnerColor="border-teal-400"
                  onGenerate={handleGenerateCB}
                >
                  <CheckboxList questions={cbQuestions} />
                </GeneratorSection>
              </div>
            </TabsContent>

            {/* Exam */}
            <TabsContent value="exam">
              {examActive ? (
                <KnowledgeExamSession
                  questions={examQuestions}
                  onFinish={() => setExamActive(false)}
                />
              ) : (
                <KnowledgeExamReady
                  typeCounts={typeCounts}
                  totalCount={examQuestions.length}
                  onStart={() => setExamActive(true)}
                />
              )}
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  )
}
