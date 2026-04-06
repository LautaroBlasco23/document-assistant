import * as React from 'react'
import { Sparkles, BookOpen, Zap, ChevronDown, ChevronUp } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Badge } from '../../components/ui/badge'
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

const MOCK_FLASHCARDS = [
  { front: 'What is the core principle of this topic?', back: 'The fundamental idea that drives all related concepts and provides the theoretical foundation for practical applications.' },
  { front: 'What are the main trade-offs to consider?', back: 'Speed vs. accuracy, simplicity vs. flexibility, and short-term vs. long-term maintainability.' },
  { front: 'How does theory translate to practice?', back: 'By adapting core principles to the specific constraints and requirements of the real-world environment, iterating based on feedback.' },
  { front: 'What is the most common pitfall?', back: 'Over-engineering: adding unnecessary complexity before validating the simpler solution works.' },
]

export function ContentTab({ treeId: _treeId, selectedChapter, chapters, onChapterChange }: ContentTabProps) {
  const [summaryStatus, setSummaryStatus] = React.useState<GenerateStatus>('idle')
  const [flashcardsStatus, setFlashcardsStatus] = React.useState<GenerateStatus>('idle')
  const [expandedCard, setExpandedCard] = React.useState<number | null>(null)

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

          {/* Generation actions */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Summary card */}
            <div className="border border-gray-200 rounded-lg p-4 flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-blue-500" />
                <span className="text-sm font-semibold text-gray-800">Summary</span>
                {summaryStatus === 'done' && <Badge variant="success">Generated</Badge>}
              </div>
              <p className="text-xs text-gray-500">
                A structured summary of the chapter based on knowledge documents.
              </p>
              {summaryStatus === 'idle' && (
                <Button variant="secondary" size="sm" onClick={() => void handleGenerateSummary()}>
                  <Sparkles className="h-3.5 w-3.5 mr-1" />
                  Generate Summary
                </Button>
              )}
              {summaryStatus === 'loading' && (
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <div className="h-3.5 w-3.5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
                  Generating from knowledge documents...
                </div>
              )}
              {summaryStatus === 'done' && (
                <div className="bg-gray-50 rounded-md p-3 text-xs text-gray-700 leading-relaxed whitespace-pre-line">
                  {MOCK_SUMMARY}
                </div>
              )}
            </div>

            {/* Flashcards card */}
            <div className="border border-gray-200 rounded-lg p-4 flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <Zap className="h-4 w-4 text-yellow-500" />
                <span className="text-sm font-semibold text-gray-800">Flashcards</span>
                {flashcardsStatus === 'done' && <Badge variant="success">{MOCK_FLASHCARDS.length} cards</Badge>}
              </div>
              <p className="text-xs text-gray-500">
                Q&A flashcards extracted from key concepts in the documents.
              </p>
              {flashcardsStatus === 'idle' && (
                <Button variant="secondary" size="sm" onClick={() => void handleGenerateFlashcards()}>
                  <Sparkles className="h-3.5 w-3.5 mr-1" />
                  Generate Flashcards
                </Button>
              )}
              {flashcardsStatus === 'loading' && (
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <div className="h-3.5 w-3.5 rounded-full border-2 border-yellow-400 border-t-transparent animate-spin" />
                  Extracting concepts...
                </div>
              )}
              {flashcardsStatus === 'done' && (
                <div className="flex flex-col gap-2">
                  {MOCK_FLASHCARDS.map((card, i) => (
                    <div
                      key={i}
                      className="border border-gray-200 rounded-md overflow-hidden cursor-pointer"
                      onClick={() => setExpandedCard(expandedCard === i ? null : i)}
                    >
                      <div className="flex items-center justify-between px-3 py-2 bg-white hover:bg-gray-50">
                        <span className="text-xs font-medium text-gray-700 flex-1 pr-2">{card.front}</span>
                        {expandedCard === i ? (
                          <ChevronUp className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                        ) : (
                          <ChevronDown className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                        )}
                      </div>
                      {expandedCard === i && (
                        <div className="px-3 py-2 bg-blue-50 border-t border-gray-200">
                          <p className="text-xs text-gray-600">{card.back}</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
