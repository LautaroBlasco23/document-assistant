import * as React from 'react'
import * as RadixDialog from '@radix-ui/react-dialog'
import { ZoomIn, ZoomOut, X } from 'lucide-react'
import { Button } from '../ui/button'
import { cn } from '../../lib/cn'

interface PdfViewerProps {
  fileUrl: string
  filename: string
  onClose: () => void
}

export function PdfViewer({ fileUrl, filename, onClose }: PdfViewerProps) {
  const [scale, setScale] = React.useState(100)

  const zoomIn = () => {
    setScale((prev) => Math.min(prev + 25, 300))
  }

  const zoomOut = () => {
    setScale((prev) => Math.max(prev - 25, 25))
  }

  const handleKeyDown = React.useCallback((e: KeyboardEvent) => {
    if (e.key === '+' || e.key === '=') zoomIn()
    if (e.key === '-') zoomOut()
    if (e.key === 'Escape') onClose()
  }, [onClose])

  React.useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  return (
    <RadixDialog.Root open onOpenChange={(open) => !open && onClose()}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 bg-black/50 z-40" />
        <RadixDialog.Content
          className={cn(
            'fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
            'max-w-5xl w-[95vw] h-[90vh] flex flex-col bg-white rounded-lg shadow-xl p-0',
          )}
        >
          <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700 truncate max-w-[200px]" title={filename}>
                {filename}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={zoomOut} title="Zoom out (-)">
                <ZoomOut className="h-4 w-4" />
              </Button>
              <span className="text-xs text-gray-600 w-12 text-center">{scale}%</span>
              <Button variant="ghost" size="sm" onClick={zoomIn} title="Zoom in (+)">
                <ZoomIn className="h-4 w-4" />
              </Button>
              <div className="w-px h-6 bg-gray-300 mx-2" />
              <Button variant="ghost" size="sm" onClick={() => window.open(fileUrl, '_blank')} title="Open in new tab">
                Open in new tab
              </Button>
              <div className="w-px h-6 bg-gray-300 mx-2" />
              <Button variant="ghost" size="sm" onClick={onClose} title="Close (Esc)">
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <div className="flex-1 overflow-auto bg-gray-100">
            <iframe
              src={fileUrl}
              className="w-full h-full border-0"
              title={filename}
            />
          </div>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  )
}
