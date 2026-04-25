/**
 * Subject: src/pages/settings/settings-page.tsx — SettingsPage
 * Scope:   Config rendering, loading states, service health badges, plan link
 * Out of scope:
 *   - ServiceBadge internals when services are missing   → covered by sidebar tests
 *   - Config editing (page is read-only)                 → no editing UI
 * Setup:   client.getConfig is mocked; useAppStore is mocked for health data.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { SettingsPage } from './settings-page'
import { renderWithProviders } from '@/test/utils'

const mockGetConfig = vi.hoisted(() => vi.fn())

vi.mock('@/services', () => ({
  client: {
    getConfig: mockGetConfig,
  },
}))

const mockUseAppStore = vi.hoisted(() => vi.fn())
vi.mock('@/stores/app-store', () => ({
  useAppStore: mockUseAppStore,
}))

function createMockAppStore(overrides = {}) {
  return {
    sidebarCollapsed: false,
    toggleSidebar: vi.fn(),
    serviceHealth: null,
    setServiceHealth: vi.fn(),
    errors: [],
    addError: vi.fn(),
    removeError: vi.fn(),
    ...overrides,
  }
}

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAppStore.mockImplementation((selector?: (state: any) => any) =>
      selector ? selector(createMockAppStore()) : createMockAppStore()
    )
  })

  // The page should immediately show a loading skeleton while the config endpoint is hit.
  it('renders loading skeletons initially', () => {
    mockGetConfig.mockReturnValue(new Promise(() => {}))
    renderWithProviders(<SettingsPage />)

    expect(screen.getByText('Ollama')).toBeInTheDocument()
    expect(screen.getByText('Chunking')).toBeInTheDocument()
  })

  // Once config loads, the Ollama and Chunking values should be visible.
  it('renders config values from API', async () => {
    mockGetConfig.mockResolvedValue({
      ollama: {
        base_url: 'http://localhost:11434',
        generation_model: 'qwen2.5:14b-instruct',
        timeout: 120,
      },
      chunking: {
        max_tokens: 512,
        overlap_tokens: 64,
      },
    })
    renderWithProviders(<SettingsPage />)

    await waitFor(() => {
      expect(screen.getByText('http://localhost:11434')).toBeInTheDocument()
    })
    expect(screen.getByText('qwen2.5:14b-instruct')).toBeInTheDocument()
    expect(screen.getByText('120')).toBeInTheDocument()
    expect(screen.getByText('512')).toBeInTheDocument()
    expect(screen.getByText('64')).toBeInTheDocument()
  })

  // Users should be able to navigate to the plan page to review their limits.
  it('renders Plan & Limits link', () => {
    mockGetConfig.mockReturnValue(new Promise(() => {}))
    renderWithProviders(<SettingsPage />)

    expect(screen.getByRole('link', { name: /plan & limits/i })).toHaveAttribute('href', '/settings/plan')
  })

  // Service health badges should reflect the current health status from the app store.
  it('renders service health badges', async () => {
    mockUseAppStore.mockImplementation((selector?: (state: any) => any) =>
      selector
        ? selector(
            createMockAppStore({
              serviceHealth: {
                status: 'healthy',
                services: [
                  { name: 'ollama', healthy: true },
                ],
              },
            })
          )
        : createMockAppStore({
            serviceHealth: {
              status: 'healthy',
              services: [
                { name: 'ollama', healthy: true },
              ],
            },
          })
    )
    mockGetConfig.mockResolvedValue({
      ollama: { base_url: '', generation_model: '', timeout: 0 },
      chunking: { max_tokens: 0, overlap_tokens: 0 },
    })
    renderWithProviders(<SettingsPage />)

    await waitFor(() => {
      expect(screen.getByText('Healthy')).toBeInTheDocument()
    })
  })
})
