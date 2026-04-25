/**
 * Subject: src/components/ui/progress.tsx — Progress component
 * Scope:   Determinate value rendering, indeterminate pulse mode, boundary values (0 and 100)
 * Out of scope:
 *   - Animation timing details
 *   - Accessibility tree beyond role and aria attributes
 */

import { render, screen } from '@testing-library/react'
import { Progress } from './progress'

describe('Progress', () => {
  // A determinate progress bar should show the correct percentage width.
  it('renders determinate value correctly', () => {
    render(<Progress value={45} />)
    const bar = screen.getByRole('progressbar')
    expect(bar).toHaveAttribute('aria-valuenow', '45')
    const fill = bar.firstChild as HTMLElement
    expect(fill).toHaveStyle('width: 45%')
  })

  // Indeterminate mode shows a pulsing bar without a fixed width percentage.
  it('renders indeterminate pulse mode', () => {
    render(<Progress indeterminate />)
    const bar = screen.getByRole('progressbar')
    expect(bar).not.toHaveAttribute('aria-valuenow')
    const fill = bar.firstChild as HTMLElement
    expect(fill).toHaveClass('animate-pulse')
    expect(fill).toHaveClass('w-1/3')
  })

  // Boundary: value of 0 should result in 0% width.
  it('renders 0% when value is 0', () => {
    render(<Progress value={0} />)
    const fill = screen.getByRole('progressbar').firstChild as HTMLElement
    expect(fill).toHaveStyle('width: 0%')
  })

  // Boundary: value of 100 should result in 100% width.
  it('renders 100% when value is 100', () => {
    render(<Progress value={100} />)
    const fill = screen.getByRole('progressbar').firstChild as HTMLElement
    expect(fill).toHaveStyle('width: 100%')
  })
})
