/**
 * Subject: src/components/layout/health-banner.tsx — HealthBanner
 * Scope:   Visibility logic based on service health, dismiss interaction
 * Out of scope:
 *   - Health polling logic  → use-health.test.tsx
 *   - MainLayout wiring     → main-layout.test.tsx
 * Setup: Pure component; state is internal.
 */

import { describe, it, expect } from 'vitest'
import { HealthBanner } from './health-banner'
import { renderWithProviders, screen } from '@/test/utils'
import userEvent from '@testing-library/user-event'

describe('HealthBanner', () => {
  it('is hidden when health data is null', () => {
    // If the app hasn't fetched health status yet, the banner should not take up space.
    const { container } = renderWithProviders(<HealthBanner health={null} />)

    expect(container.firstChild).toBeNull()
  })

  it('is hidden when all services are healthy', () => {
    // A fully healthy system needs no warning banner.
    const health = {
      status: 'healthy',
      services: [
        { name: 'LLM', healthy: true },
        { name: 'PostgreSQL', healthy: true },
      ],
    }

    const { container } = renderWithProviders(<HealthBanner health={health} />)

    expect(container.firstChild).toBeNull()
  })

  it('shows a warning when at least one service is unhealthy', () => {
    // Degraded services should be surfaced immediately to the user.
    const health = {
      status: 'degraded',
      services: [
        { name: 'LLM', healthy: false, error: 'timeout' },
        { name: 'PostgreSQL', healthy: true },
      ],
    }

    renderWithProviders(<HealthBanner health={health} />)

    expect(screen.getByText(/some services are unavailable/i)).toBeInTheDocument()
    expect(screen.getByText('LLM')).toBeInTheDocument()
  })

  it('hides the banner after clicking the dismiss button', async () => {
    // Users should be able to dismiss the warning once they've acknowledged it.
    const health = {
      status: 'degraded',
      services: [{ name: 'PostgreSQL', healthy: false, error: 'down' }],
    }

    const user = userEvent.setup()
    const { container } = renderWithProviders(<HealthBanner health={health} />)

    expect(screen.getByText(/some services are unavailable/i)).toBeInTheDocument()

    const dismissBtn = screen.getByLabelText('Dismiss')
    await user.click(dismissBtn)

    expect(container.firstChild).toBeNull()
  })

  it('lists multiple unhealthy services in the message', () => {
    // When several services fail, the banner should name all of them.
    const health = {
      status: 'degraded',
      services: [
        { name: 'LLM', healthy: false },
        { name: 'PostgreSQL', healthy: false },
      ],
    }

    renderWithProviders(<HealthBanner health={health} />)

    const message = screen.getByText(/some services are unavailable/i)
    expect(message.textContent).toContain('LLM')
    expect(message.textContent).toContain('PostgreSQL')
  })
})
