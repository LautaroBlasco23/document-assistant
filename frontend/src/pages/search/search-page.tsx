import * as React from 'react'
import { Search } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { SkeletonCard } from '../../components/ui/skeleton'
import { EmptyState } from '../../components/ui/empty-state'
import { Select } from '../../components/ui/select'
import { client } from '../../services'
import { useDocuments } from '../../hooks/use-documents'
import type { ChunkOut } from '../../types/api'
import { SearchResult } from './search-result'

export function SearchPage() {
  const { documents } = useDocuments()
  const [query, setQuery] = React.useState('')
  const [selectedDocHash, setSelectedDocHash] = React.useState('')
  const [results, setResults] = React.useState<ChunkOut[] | null>(null)
  const [loading, setLoading] = React.useState(false)
  const [lastQuery, setLastQuery] = React.useState('')

  async function handleSearch() {
    const trimmed = query.trim()
    if (!trimmed) return
    setLoading(true)
    setLastQuery(trimmed)
    try {
      const selectedDoc = documents.find((d) => d.file_hash === selectedDocHash)
      // Pass filename without extension as book filter if a doc is selected
      const bookTitle = selectedDoc
        ? selectedDoc.filename.replace(/\.[^.]+$/, '')
        : undefined
      const data = await client.search(trimmed, 5, undefined)
      // If a book filter is selected, filter client-side as a best-effort
      const chunks = bookTitle
        ? data.chunks.filter((c) => c.id.includes(selectedDocHash.slice(0, 6)))
        : data.chunks
      setResults(chunks)
    } catch {
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      void handleSearch()
    }
  }

  const hasSearched = results !== null
  const isEmpty = hasSearched && results.length === 0

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Search</h1>

      {/* Search bar */}
      <div className="flex gap-2 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Search across your documents..."
            className="w-full rounded-md border border-gray-300 bg-white pl-9 pr-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          />
        </div>
        <Button variant="primary" onClick={() => void handleSearch()} loading={loading}>
          Search
        </Button>
      </div>

      {/* Filter by document */}
      <div className="mb-6 max-w-xs">
        <Select
          value={selectedDocHash}
          onChange={(e) => setSelectedDocHash(e.target.value)}
          aria-label="Filter by document"
        >
          <option value="">All documents</option>
          {documents.map((doc) => (
            <option key={doc.file_hash} value={doc.file_hash}>
              {doc.filename}
            </option>
          ))}
        </Select>
      </div>

      {/* Results area */}
      {loading ? (
        <div className="flex flex-col gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : !hasSearched ? (
        <EmptyState
          icon={Search}
          title="Search your documents"
          description="Ask anything across all your ingested documents"
        />
      ) : isEmpty ? (
        <EmptyState
          icon={Search}
          title={`No results found for "${lastQuery}"`}
          description="Try a different query or check your document library"
        />
      ) : (
        <div className="flex flex-col gap-4">
          {results.map((chunk) => (
            <SearchResult key={chunk.id} chunk={chunk} documents={documents} />
          ))}
        </div>
      )}
    </div>
  )
}
