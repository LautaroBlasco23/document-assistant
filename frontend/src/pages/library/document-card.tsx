import * as React from 'react'
import { useNavigate } from 'react-router-dom'
import { BookOpen, Hash, Trash2 } from 'lucide-react'
import { Card } from '../../components/ui/card'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import { Dialog } from '../../components/ui/dialog'
import type { DocumentOut } from '../../types/api'

interface DocumentCardProps {
  document: DocumentOut
  onDelete: (hash: string) => void
}

function getFormatBadge(filename: string): { label: string; variant: 'info' | 'success' | 'neutral' } {
  const ext = filename.split('.').pop()?.toLowerCase()
  if (ext === 'pdf') return { label: 'PDF', variant: 'info' }
  if (ext === 'epub') return { label: 'EPUB', variant: 'success' }
  if (ext === 'txt') return { label: 'TXT', variant: 'neutral' }
  if (ext === 'md') return { label: 'MD', variant: 'neutral' }
  return { label: ext?.toUpperCase() ?? 'FILE', variant: 'neutral' }
}

export function DocumentCard({ document, onDelete }: DocumentCardProps) {
  const navigate = useNavigate()
  const [deleteOpen, setDeleteOpen] = React.useState(false)

  const format = getFormatBadge(document.filename)
  const hashExcerpt = document.file_hash.slice(0, 8)

  return (
    <>
      <Card
        className="flex flex-col gap-3 hover:shadow-md transition-shadow cursor-pointer"
        onClick={() => navigate(`/documents/${document.file_hash}`)}
      >
        {/* Top area: filename + format badge */}
        <div className="flex items-start justify-between gap-2">
          <span
            className="font-medium text-gray-800 truncate flex-1 min-w-0"
            title={document.filename}
          >
            {document.filename}
          </span>
          <Badge variant={format.variant} className="shrink-0">
            {format.label}
          </Badge>
        </div>

        {/* Stats row */}
        <div className="flex items-center gap-4 text-xs text-gray-400">
          <span className="flex items-center gap-1">
            <BookOpen className="h-3.5 w-3.5" />
            {document.num_chapters} chapters
          </span>
          <span className="flex items-center gap-1 font-mono">
            <Hash className="h-3.5 w-3.5" />
            {hashExcerpt}
          </span>
        </div>

        {/* Footer row: Open + Delete */}
        <div className="flex items-center justify-between pt-1 border-t border-gray-100 mt-auto">
          <Button
            variant="primary"
            size="sm"
            onClick={(e) => { e.stopPropagation(); navigate(`/documents/${document.file_hash}`) }}
          >
            Open
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => { e.stopPropagation(); setDeleteOpen(true) }}
            className="text-red-500 hover:text-red-600 hover:bg-red-50"
            aria-label="Delete document"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </Card>

      <Dialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete document"
        description="This will permanently remove the document and all its data."
        onConfirm={() => onDelete(document.file_hash)}
        confirmLabel="Delete"
        variant="destructive"
      />
    </>
  )
}
