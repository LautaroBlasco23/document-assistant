import * as React from 'react'
import * as RadixDialog from '@radix-ui/react-dialog'
import { X, Loader2, ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '../ui/button'
import { cn } from '../../lib/cn'

interface EpubViewerProps {
  fileUrl: string
  filename: string
  onClose: () => void
}

export function EpubViewer({ fileUrl, filename, onClose }: EpubViewerProps) {
  const containerRef = React.useRef<HTMLDivElement>(null)
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)
  const [toc, setToc] = React.useState<{ label: string; href: string }[]>([])
  const [currentChapter, setCurrentChapter] = React.useState(0)
  const renditionRef = React.useRef<unknown>(null)
  const bookRef = React.useRef<unknown>(null)

  React.useEffect(() => {
    let mounted = true

    async function loadEpub() {
      try {
        const ePub = (await import('epubjs')).default
        const book = ePub(fileUrl)
        bookRef.current = book

        await book.ready

        if (!mounted) return

        const navigation = await book.loaded.navigation
        if (navigation?.toc) {
          setToc(navigation.toc.map((item: { label: string; href: string }) => ({
            label: item.label,
            href: item.href,
          })))
        }

        if (containerRef.current) {
          const rendition = book.renderTo(containerRef.current, {
            width: '100%',
            height: '100%',
            spread: 'auto',
          })
          renditionRef.current = rendition

          rendition.on('rendered', () => {
            if (mounted) setLoading(false)
          })

          rendition.on('relocated', (location: { start: { index: number } }) => {
            if (mounted && location.start?.index !== undefined) {
              setCurrentChapter(location.start.index)
            }
          })

          await rendition.display()
        }
      } catch (err) {
        console.error('EPUB load error:', err)
        if (mounted) {
          setError('Failed to load EPUB')
          setLoading(false)
        }
      }
    }

    loadEpub()

    return () => {
      mounted = false
      if (bookRef.current) {
        (bookRef.current as { destroy?: () => void }).destroy?.()
      }
    }
  }, [fileUrl])

  const goToPrev = () => {
    if (renditionRef.current) {
      (renditionRef.current as { prev: () => void }).prev()
    }
  }

  const goToNext = () => {
    if (renditionRef.current) {
      (renditionRef.current as { next: () => void }).next()
    }
  }

  const goToChapter = (href: string) => {
    if (renditionRef.current) {
      (renditionRef.current as { display: (href: string) => void }).display(href)
    }
  }

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'ArrowLeft') goToPrev()
    if (e.key === 'ArrowRight') goToNext()
    if (e.key === 'Escape') onClose()
  }

  React.useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <RadixDialog.Root open onOpenChange={(open) => !open && onClose()}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 bg-black/50 z-40" />
        <RadixDialog.Content
          className={cn(
            'fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
            'max-w-6xl w-[95vw] h-[90vh] flex flex-col bg-white rounded-lg shadow-xl p-0',
          )}
        >
          <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700 truncate max-w-[200px]" title={filename}>
                {filename}
              </span>
              {toc.length > 0 && (
                <span className="text-xs text-gray-500">
                  Chapter {currentChapter + 1} of {toc.length}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={goToPrev} title="Previous page (←)">
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="sm" onClick={goToNext} title="Next page (→)">
                <ChevronRight className="h-4 w-4" />
              </Button>
              <div className="w-px h-6 bg-gray-300 mx-2" />
              <Button variant="ghost" size="sm" onClick={onClose} title="Close (Esc)">
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <div className="flex-1 flex overflow-hidden">
            {toc.length > 0 && (
              <div className="w-48 border-r bg-gray-50 overflow-y-auto">
                <div className="p-2">
                  <p className="text-xs font-medium text-gray-500 px-2 py-1">Table of Contents</p>
                  {toc.map((item, index) => (
                    <button
                      key={item.href}
                      onClick={() => goToChapter(item.href)}
                      className={`w-full text-left px-2 py-1.5 text-sm rounded hover:bg-gray-100 ${
                        index === currentChapter ? 'bg-gray-200 font-medium' : ''
                      }`}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
            <div className="flex-1 overflow-auto bg-gray-200">
              {loading && (
                <div className="flex items-center justify-center h-full">
                  <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
                </div>
              )}
              {error && (
                <div className="flex items-center justify-center h-full">
                  <p className="text-red-500">{error}</p>
                </div>
              )}
              <div ref={containerRef} className="h-full" />
            </div>
          </div>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  )
}
