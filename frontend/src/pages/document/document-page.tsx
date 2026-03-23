import { useParams, useSearchParams, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { useDocuments } from '../../hooks/use-documents'
import { useDocumentStructure } from '../../hooks/use-document-structure'
import { DocumentLayout } from '../../components/layout/document-layout'
import { SkeletonLine, SkeletonBlock } from '../../components/ui/skeleton'
import { Button } from '../../components/ui/button'
import { FlashcardTab } from './flashcard-tab'
import { SummaryTab } from './summary-tab'
import type { Tab } from '../../types/domain'
import { useState } from 'react'

const VALID_TABS: Tab[] = ['flashcards', 'summary']

function isValidTab(value: string | null): value is Tab {
  return VALID_TABS.includes(value as Tab)
}

export function DocumentPage() {
  const { hash } = useParams<{ hash: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const { documents, loading: docsLoading } = useDocuments()
  const { structure, loading: structureLoading } = useDocumentStructure(hash ?? '')
  const [selectedChapter, setSelectedChapter] = useState<number>(1)

  const rawTab = searchParams.get('tab')
  const activeTab: Tab = isValidTab(rawTab) ? rawTab : 'summary'

  const handleTabChange = (tab: Tab) => {
    setSearchParams({ tab }, { replace: true })
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
        return <FlashcardTab docHash={hash} chapter={selectedChapter} structure={structure} />
      case 'summary':
        return <SummaryTab docHash={hash} chapter={selectedChapter} structure={structure} />
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
    >
      {renderTabContent()}
    </DocumentLayout>
  )
}
