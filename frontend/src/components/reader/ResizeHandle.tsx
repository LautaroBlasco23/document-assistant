import * as React from 'react'
import { cn } from '../../lib/cn'

interface ResizeHandleProps {
  direction?: 'horizontal' | 'vertical'
  onResizeStart?: () => void
  onResize: (delta: number) => void
  onResizeEnd?: () => void
}

export function ResizeHandle({
  direction = 'horizontal',
  onResizeStart,
  onResize,
  onResizeEnd,
}: ResizeHandleProps) {
  const handlePointerDown = (e: React.PointerEvent) => {
    e.preventDefault()
    onResizeStart?.()

    const cursor = direction === 'horizontal' ? 'col-resize' : 'row-resize'
    const prevUserSelect = document.body.style.userSelect
    const prevCursor = document.body.style.cursor
    document.body.style.userSelect = 'none'
    document.body.style.cursor = cursor

    const startPos = direction === 'horizontal' ? e.clientX : e.clientY
    let rafId: number | null = null
    let latestDelta = 0

    const handlePointerMove = (moveEvent: PointerEvent) => {
      const currentPos = direction === 'horizontal' ? moveEvent.clientX : moveEvent.clientY
      latestDelta = currentPos - startPos

      if (rafId !== null) return
      rafId = requestAnimationFrame(() => {
        rafId = null
        onResize(latestDelta)
      })
    }

    const handlePointerUp = () => {
      if (rafId !== null) {
        cancelAnimationFrame(rafId)
        rafId = null
      }
      document.body.style.userSelect = prevUserSelect
      document.body.style.cursor = prevCursor
      onResizeEnd?.()
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('pointerup', handlePointerUp)
    }

    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerup', handlePointerUp)
  }

  return (
    <div
      onPointerDown={handlePointerDown}
      className={cn(
        'shrink-0 bg-transparent hover:bg-blue-300/50 active:bg-blue-400/70 transition-colors touch-none',
        direction === 'horizontal'
          ? 'w-1.5 cursor-col-resize self-stretch'
          : 'h-1.5 cursor-row-resize'
      )}
    />
  )
}
