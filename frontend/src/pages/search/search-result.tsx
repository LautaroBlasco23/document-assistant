import { useNavigate } from 'react-router-dom'
import { cn } from '../../lib/cn'
import { Card } from '../../components/ui/card'
import type { ChunkOut, DocumentOut } from '../../types/api'

interface SearchResultProps {
  chunk: ChunkOut
  documents: DocumentOut[]
}

function getScoreColor(score: number): string {
  if (score > 0.8) return 'bg-green-500'
  if (score > 0.6) return 'bg-amber-500'
  return 'bg-red-500'
}

export function SearchResult({ chunk, documents }: SearchResultProps) {
  const navigate = useNavigate()

  // Attempt to find the document by matching hash prefix from chunk id
  const hashPrefix = chunk.id.split('-')[0]
  const matchedDoc = documents.find(
    (d) => d.file_hash.startsWith(hashPrefix) || hashPrefix.startsWith(d.file_hash.slice(0, 6)),
  )
  const docName = matchedDoc?.filename ?? 'Document'

  const score = chunk.score ?? 0
  const scorePercent = Math.round(score * 100)
  const snippetText =
    chunk.text.length > 250 ? chunk.text.slice(0, 250) + '...' : chunk.text

  function handleClick() {
    if (matchedDoc) {
      navigate(`/documents/${matchedDoc.file_hash}?tab=chat`)
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      className="cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 rounded-card"
      onClick={handleClick}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleClick() }}
    >
      <Card className="hover:shadow-md transition-shadow">
        {/* Document name */}
        <p className="font-medium text-gray-800 text-sm truncate" title={docName}>
          {docName}
        </p>

        {/* Chapter + page */}
        <p className="text-xs text-gray-400 mt-0.5">
          Chapter {chunk.chapter}
          {chunk.page !== undefined && ` · Page ${chunk.page}`}
        </p>

        {/* Relevance score bar */}
        <div className="flex items-center gap-2 mt-2">
          <div className="flex-1 bg-gray-100 rounded-full h-1.5 overflow-hidden">
            <div
              className={cn('h-1.5 rounded-full', getScoreColor(score))}
              style={{ width: `${scorePercent}%` }}
            />
          </div>
          <span className="text-xs text-gray-500 tabular-nums">{scorePercent}%</span>
        </div>

        {/* Text snippet */}
        <p className="text-gray-700 text-sm mt-2 leading-relaxed">{snippetText}</p>
      </Card>
    </div>
  )
}
