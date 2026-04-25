import * as React from 'react'
import { cn } from '../../lib/cn'

interface ResizeHandleProps {
  direction?: 'horizontal' | 'vertical'
  onResizeStart?: () => void
  onResize: (delta: number) => void
}

export function ResizeHandle({
  direction = 'horizontal',
  onResizeStart,
  onResize,
}: ResizeHandleProps) {
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault()
    onResizeStart?.()
    document.body.style.userSelect = 'none'

    const startPos = direction === 'horizontal' ? e.clientX : e.clientY

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const currentPos =
        direction === 'horizontal' ? moveEvent.clientX : moveEvent.clientY
      onResize(currentPos - startPos)
    }

    const handleMouseUp = () => {
      document.body.style.userSelect = ''
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
  }

  return (
    <div
      onMouseDown={handleMouseDown}
      className={cn(
        'shrink-0 bg-transparent hover:bg-blue-300/50 active:bg-blue-400/70 transition-colors',
        direction === 'horizontal'
          ? 'w-1.5 cursor-col-resize self-stretch'
          : 'h-1.5 cursor-row-resize'
      )}
    />
  )
}
