import { X } from 'lucide-react'
import { Card } from '../../components/ui/card'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import { Progress } from '../../components/ui/progress'
import type { UploadEntry } from '../../stores/upload-store'

interface UploadingDocumentCardProps {
  upload: UploadEntry
  onDismiss: (id: string) => void
}

function getFormatBadge(filename: string): { label: string; variant: 'info' | 'success' | 'neutral' } {
  const ext = filename.split('.').pop()?.toLowerCase()
  if (ext === 'pdf') return { label: 'PDF', variant: 'info' }
  if (ext === 'epub') return { label: 'EPUB', variant: 'success' }
  if (ext === 'txt') return { label: 'TXT', variant: 'neutral' }
  if (ext === 'md') return { label: 'MD', variant: 'neutral' }
  return { label: ext?.toUpperCase() ?? 'FILE', variant: 'neutral' }
}

export function UploadingDocumentCard({ upload, onDismiss }: UploadingDocumentCardProps) {
  const format = getFormatBadge(upload.filename)
  const isFailed = upload.status === 'failed'
  const isCompleted = upload.status === 'completed'

  return (
    <Card className="flex flex-col gap-3 opacity-80">
      {/* Top area: filename + format badge */}
      <div className="flex items-start justify-between gap-2">
        <span
          className="font-medium text-gray-800 truncate flex-1 min-w-0"
          title={upload.filename}
        >
          {upload.filename}
        </span>
        <Badge variant={format.variant} className="shrink-0">
          {format.label}
        </Badge>
      </div>

      {/* Middle area: progress or error */}
      {isFailed ? (
        <p className="text-sm text-red-600 truncate">
          {upload.error ?? 'Upload failed'}
        </p>
      ) : (
        <div className="space-y-1.5">
          <Progress
            value={isCompleted ? 100 : 0}
            indeterminate={!isCompleted}
          />
          <p className="text-xs text-gray-500 truncate">
            {upload.progress ?? (upload.status === 'uploading' ? 'Uploading...' : 'Processing...')}
          </p>
        </div>
      )}

      {/* Footer row */}
      <div className="flex items-center justify-end pt-1 border-t border-gray-100 mt-auto">
        {isFailed ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDismiss(upload.id)}
            aria-label="Dismiss"
          >
            <X className="h-4 w-4 mr-1" />
            Dismiss
          </Button>
        ) : isCompleted ? (
          <span className="text-xs text-green-600 font-medium">Done!</span>
        ) : (
          <span className="text-xs text-gray-400 italic">Processing&hellip;</span>
        )}
      </div>
    </Card>
  )
}
