import { useParams, useSearchParams, Link, useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { useDocuments } from '../../hooks/use-documents'
import { useDocumentStructure } from '../../hooks/use-document-structure'
import { DocumentLayout } from '../../components/layout/document-layout'
import { SkeletonLine, SkeletonBlock } from '../../components/ui/skeleton'
import { Button } from '../../components/ui/button'
import { FlashcardTab } from './flashcard-tab'
import { SummaryTab } from './summary-tab'
import { ExamTab } from './exam-tab'
import type { Tab } from '../../types/domain'
import { useState } from 'react'
import { useDocumentStore } from '../../stores/document-store'

const VALID_TABS: Tab[] = ['flashcards', 'summary', 'exam']

function isValidTab(value: string | null): value is Tab {
  return VALID_TABS.includes(value as Tab)
}

export function DocumentPage() {
  const { hash } = useParams<{ hash: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const { documents, loading: docsLoading } = useDocuments()
  const { structure, loading: structureLoading, refresh: refreshStructure } = useDocumentStructure(hash ?? '')
  const [selectedChapter, setSelectedChapter] = useState<number>(1)
  const clearContent = useDocumentStore((s) => s.clearContent)

  const selectedChapterData = structure?.chapters.find((ch) => ch.number === selectedChapter)
  const currentChapterIndex = selectedChapterData?.chapter_index ?? 0

  const rawTab = searchParams.get('tab')
  const activeTab: Tab = isValidTab(rawTab) ? rawTab : 'summary'

  const handleTabChange = (tab: Tab) => {
    setSearchParams({ tab }, { replace: true })
  }

  const handleChapterRemoved = (removedChapterNumber: number) => {
    // Navigate to the first available chapter that isn't the removed one
    const remaining = structure?.chapters.filter((ch) => ch.number !== removedChapterNumber) ?? []
    if (remaining.length > 0) {
      setSelectedChapter(remaining[0].number)
    } else {
      setSelectedChapter(1)
    }
  }

  const handleEditSave = async (newHash?: string) => {
    if (newHash) {
      clearContent(hash!)
      await refreshStructure()
      navigate(`/documents/${newHash}`, { replace: true })
    } else {
      await refreshStructure()
    }
  }

  const loading = docsLoading && documents.length === 0

  if (!hash) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <p className="text-gray-500">Invalid document URL.</p>
        <Link to="/" className="text-primary hover:underline text-sm flex items-center gap-1">
          <ArrowLeft className="h-4 w-4" /> Back to Library
        </Link>
      </div>
    )
  }

  if (loading || structureLoading) {
    return (
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <SkeletonBlock height="h-8" className="w-8 rounded-md" />
          <SkeletonLine className="w-64" />
        </div>
        <SkeletonLine className="w-40" />
        <SkeletonBlock height="h-10" className="w-full" />
        <SkeletonBlock height="h-64" className="w-full" />
      </div>
    )
  }

  const document = documents.find((doc) => doc.file_hash === hash)

  if (!document) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <p className="text-gray-600 font-medium">Document not found</p>
        <p className="text-gray-400 text-sm">
          The document with hash <code className="font-mono text-xs bg-gray-100 px-1 py-0.5 rounded">{hash.slice(0, 8)}...</code> could not be found.
        </p>
        <Link to="/">
          <Button variant="secondary" size="sm">
            <ArrowLeft className="h-4 w-4" /> Back to Library
          </Button>
        </Link>
      </div>
    )
  }

  const renderTabContent = () => {
    switch (activeTab) {
      case 'flashcards':
        return <FlashcardTab docHash={hash} chapter={selectedChapter} chapterIndex={currentChapterIndex} structure={structure} />
      case 'summary':
        return <SummaryTab docHash={hash} chapter={selectedChapter} chapterIndex={currentChapterIndex} structure={structure} />
      case 'exam':
        return <ExamTab docHash={hash} chapter={selectedChapter} chapterIndex={currentChapterIndex} structure={structure} />
      default:
        return null
    }
  }

  return (
    <DocumentLayout
      document={document}
      structure={structure}
      activeTab={activeTab}
      onTabChange={handleTabChange}
      selectedChapter={selectedChapter}
      onChapterChange={setSelectedChapter}
      onChapterRemoved={handleChapterRemoved}
      onEditSave={handleEditSave}
    >
      {renderTabContent()}
    </DocumentLayout>
  )
}
