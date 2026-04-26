/**
 * Subject: src/components/ui/badge.tsx — Badge component
 * Scope:   Rendering each variant, applying custom className, displaying children
 * Out of scope:
 *   - Interactive behavior (Badge is non-interactive)
 *   - Accessibility beyond basic rendering
 */

import { render, screen } from '@testing-library/react'
import { Badge } from './badge'

describe('Badge', () => {
  // Renders with default styling and displays child text.
  it('renders children text', () => {
    render(<Badge variant="neutral">Draft</Badge>)
    expect(screen.getByText('Draft')).toBeInTheDocument()
  })

  // Each variant maps to a distinct color scheme; we verify the correct Tailwind classes are present.
  it.each([
    ['success', 'bg-success-light'],
    ['warning', 'bg-warning-light'],
    ['danger', 'bg-danger-light'],
    ['info', 'bg-primary-light'],
    ['neutral', 'bg-surface-100'],
  ] as const)('applies %s variant classes', (variant, expectedClass) => {
    render(<Badge variant={variant}>{variant}</Badge>)
    expect(screen.getByText(variant)).toHaveClass(expectedClass)
  })

  // Consumers can extend or override styling via className; the custom class should be present.
  it('applies custom className', () => {
    render(<Badge variant="info" className="my-extra-class">Info</Badge>)
    expect(screen.getByText('Info')).toHaveClass('my-extra-class')
  })
})
