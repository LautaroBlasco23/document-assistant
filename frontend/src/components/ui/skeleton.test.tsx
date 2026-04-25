/**
 * Subject: src/components/ui/skeleton.tsx — SkeletonLine, SkeletonBlock, SkeletonCard
 * Scope:   Rendering without crash, presence of animation classes
 * Out of scope:
 *   - Animation timing and keyframes
 *   - Responsive sizing
 */

import { render } from '@testing-library/react'
import { SkeletonLine, SkeletonBlock, SkeletonCard } from './skeleton'

describe('Skeleton', () => {
  // SkeletonLine should render a div with the expected animation class.
  it('SkeletonLine renders without crash and has animation class', () => {
    const { container } = render(<SkeletonLine />)
    const line = container.querySelector('.animate-skeleton')
    expect(line).toBeInTheDocument()
    expect(line).toHaveClass('h-4')
  })

  // SkeletonBlock should render a div with the expected animation class and default height.
  it('SkeletonBlock renders without crash and has animation class', () => {
    const { container } = render(<SkeletonBlock />)
    const block = container.querySelector('.animate-skeleton')
    expect(block).toBeInTheDocument()
    expect(block).toHaveClass('h-20')
  })

  // SkeletonCard should render a container with nested skeleton elements.
  it('SkeletonCard renders without crash and contains skeleton elements', () => {
    const { container } = render(<SkeletonCard />)
    expect(container.firstChild).toBeInTheDocument()
    const animated = container.querySelectorAll('.animate-skeleton')
    expect(animated.length).toBeGreaterThanOrEqual(3)
  })
})
