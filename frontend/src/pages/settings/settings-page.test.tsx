/**
 * Subject: src/pages/settings/settings-page.tsx — SettingsPage
 * Scope:   Section rendering, theme selection, agent selection, plan link
 * Out of scope:
 *   - Service health dots   → covered by sidebar tests
 *   - Config file values    → read-only, not fetched by this page
 * Setup:   No API mocks needed — page reads from ThemeProvider and Zustand stores only.
 */

import { describe, it, expect, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { SettingsPage } from './settings-page'
import { renderWithProviders } from '@/test/utils'

vi.mock('@/stores/reference-data-store', () => {
  const store = {
    models: [],
    modelsProvider: '',
    modelsCurrentModel: '',
    modelsLoadedFilter: undefined,
    modelsLoading: false,
    agents: [],
    agentsLoaded: false,
    agentsLoading: false,
    providers: [],
    credentials: [],
    credentialsLoaded: false,
    credentialsLoading: false,
    loadModels: vi.fn().mockResolvedValue(undefined),
    loadAgents: vi.fn().mockResolvedValue(undefined),
    loadCredentials: vi.fn().mockResolvedValue(undefined),
    reset: vi.fn(),
  }
  const mockStore = vi.fn((selectorOrFn?: unknown) => {
    if (typeof selectorOrFn === 'function') return selectorOrFn(store)
    return store
  })
  mockStore.getState = vi.fn(() => store)
  mockStore.setState = vi.fn()
  return {
    useRefDataStore: mockStore,
    useRefData: vi.fn(() => ({
      models: store.models,
      modelsProvider: store.modelsProvider,
      modelsCurrentModel: store.modelsCurrentModel,
      modelsLoading: store.modelsLoading,
      agents: store.agents,
      agentsLoading: store.agentsLoading,
      providers: store.providers,
      credentials: store.credentials,
      credentialsLoading: store.credentialsLoading,
    })),
  }
})

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
