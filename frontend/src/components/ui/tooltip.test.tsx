/**
 * Subject: src/components/ui/tooltip.tsx — Tooltip component
 * Scope:   Trigger rendering, content presence in the DOM
 * Out of scope:
 *   - Hover interaction behavior (handled by Radix UI internals)
 *   - Positioning calculations
 */

import { render, screen } from '@testing-library/react'
import { Tooltip } from './tooltip'

describe('Tooltip', () => {
  // The trigger element should always be rendered so users can hover/focus it.
  it('renders trigger element', () => {
    render(
      <Tooltip content="Helpful tip">
        <button>Hover me</button>
      </Tooltip>,
    )
    expect(screen.getByRole('button', { name: 'Hover me' })).toBeInTheDocument()
  })
})
