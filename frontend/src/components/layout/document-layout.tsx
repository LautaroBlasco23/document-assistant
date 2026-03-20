import * as React from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../ui/tabs'
import { Badge } from '../ui/badge'
import { Select } from '../ui/select'
import { Button } from '../ui/button'
import { cn } from '../../lib/cn'
import type { DocumentOut, DocumentStructureOut } from '../../types/api'
import type { Tab } from '../../types/domain'

export interface DocumentLayoutProps {
  document: DocumentOut
  structure: DocumentStructureOut | null
  activeTab: Tab
  onTabChange: (tab: Tab) => void
  selectedChapter: number | undefined
  onChapterChange: (chapter: number | undefined) => void
  children: React.ReactNode
  className?: string
}

const TAB_LABELS: Record<Tab, string> = {
  chat: 'Chat',
  qa: 'Q&A',
  flashcards: 'Flashcards',
  summary: 'Summary',
}

export function DocumentLayout({
  document,
  structure,
  activeTab,
  onTabChange,
  selectedChapter,
  onChapterChange,
  children,
  className,
}: DocumentLayoutProps) {
  const navigate = useNavigate()

  const chapterCount = structure?.chapters.length ?? document.num_chapters

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      {/* Document header */}
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate('/')}
          className="shrink-0"
          aria-label="Back to library"
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-semibold text-gray-900 truncate">
            {document.filename}
          </h1>
        </div>
        <Badge variant="neutral" className="shrink-0">
          {chapterCount} {chapterCount === 1 ? 'chapter' : 'chapters'}
        </Badge>
      </div>

      {/* Chapter selector toolbar */}
      <div className="flex items-center gap-3">
        <Select
          className="max-w-xs"
          value={selectedChapter !== undefined ? String(selectedChapter) : ''}
          onChange={(e) => {
            const val = e.target.value
            onChapterChange(val === '' ? undefined : Number(val))
          }}
        >
          <option value="">All chapters</option>
          {structure?.chapters.map((ch) => (
            <option key={ch.number} value={String(ch.number)}>
              Chapter {ch.number}
              {ch.title ? `: ${ch.title}` : ''}
            </option>
          ))}
          {/* Fallback when structure not yet loaded */}
          {!structure &&
            Array.from({ length: document.num_chapters }, (_, i) => i + 1).map((n) => (
              <option key={n} value={String(n)}>
                Chapter {n}
              </option>
            ))}
        </Select>
      </div>

      {/* Tabs */}
      <Tabs
        value={activeTab}
        onValueChange={(v) => onTabChange(v as Tab)}
      >
        <TabsList>
          {(Object.keys(TAB_LABELS) as Tab[]).map((tab) => (
            <TabsTrigger key={tab} value={tab}>
              {TAB_LABELS[tab]}
            </TabsTrigger>
          ))}
        </TabsList>

        {/* Render all tab content slots; the active one is shown by Radix */}
        {(Object.keys(TAB_LABELS) as Tab[]).map((tab) => (
          <TabsContent key={tab} value={tab}>
            {activeTab === tab ? children : null}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}
