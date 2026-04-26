/**
 * Subject: src/pages/settings/settings-page.tsx — SettingsPage
 * Scope:   Section rendering, theme selection, agent selection, plan link
 * Out of scope:
 *   - Service health dots   → covered by sidebar tests
 *   - Config file values    → read-only, not fetched by this page
 * Setup:   No API mocks needed — page reads from ThemeProvider and Zustand stores only.
 */

import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import { SettingsPage } from './settings-page'
import { renderWithProviders } from '@/test/utils'

describe('SettingsPage', () => {
  // The page renders two main cards (Appearance, Agents) + plan link.
  it('renders main sections', () => {
    renderWithProviders(<SettingsPage />)

    expect(screen.getByText('Appearance')).toBeInTheDocument()
    expect(screen.getByText('Agents')).toBeInTheDocument()
  })

  // Users should be able to navigate to the plan page to review their limits.
  it('renders Plan & Limits link', () => {
    renderWithProviders(<SettingsPage />)

    expect(screen.getByRole('link', { name: /plan & limits/i })).toHaveAttribute('href', '/settings/plan')
  })

  // The appearance section exposes three theme toggle buttons.
  it('renders theme selection buttons', () => {
    renderWithProviders(<SettingsPage />)

    expect(screen.getByRole('button', { name: 'light' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'dark' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'system' })).toBeInTheDocument()
  })
})
