/**
 * Subject: src/components/reader/ImproveDialog.tsx
 * Scope:   Render states (open/closed, loading, agents, empty), agent selection,
 *          Run/Cancel callbacks.
 * Out of scope:
 *   - Radix portal internals (covered by Radix)
 *   - AgentCreationDialog internals (tested in its own suite)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ImproveDialog } from './ImproveDialog'
import { useAgents } from '../../hooks/use-agents'
import { useGenerationSettings } from '../../stores/generation-settings'
import { useModels } from '../../hooks/use-models'
import { useProviderCredentials } from '../../hooks/useProviderCredentials'

// ---- mocks ----

vi.mock('../../hooks/use-agents')
vi.mock('../../stores/generation-settings')
vi.mock('../../hooks/use-models')
vi.mock('../../hooks/useProviderCredentials')

const mockOnOpenChange = vi.fn()
const mockOnConfirm = vi.fn()
const mockSetAgent = vi.fn()

const defaultAgent = {
  id: 'agent-1',
  name: 'Scholar',
  provider: 'groq',
  model: 'llama-3.3-70b',
  prompt: 'You are a scholarly assistant.',
  temperature: 0.5,
  top_p: 0.9,
  max_tokens: 2048,
  is_default: true,
  created_at: '2024-01-01T00:00:00Z',
}

const secondAgent = {
  id: 'agent-2',
  name: 'Writer',
  provider: 'openai',
  model: 'gpt-4o',
  prompt: '',
  temperature: 0.8,
  top_p: 1.0,
  max_tokens: 4096,
  is_default: false,
  created_at: '2024-01-02T00:00:00Z',
}

const baseProps = {
  open: true,
  onOpenChange: mockOnOpenChange,
  onConfirm: mockOnConfirm,
  isImproving: false,
}

beforeEach(() => {
  vi.clearAllMocks()

  vi.mocked(useAgents).mockReturnValue({
    agents: [defaultAgent, secondAgent],
    loading: false,
    refresh: vi.fn(),
  })

  vi.mocked(useGenerationSettings).mockReturnValue({
    settings: { agent_id: 'agent-1', temperature: 0.7, top_p: 1.0, max_tokens: 1024 },
    setAgent: mockSetAgent,
    update: vi.fn(),
    clearAgent: vi.fn(),
    clearModel: vi.fn(),
  })

  vi.mocked(useModels).mockReturnValue({
    models: [],
    provider: '',
    currentModel: '',
    loading: false,
  })

  vi.mocked(useProviderCredentials).mockReturnValue({
    useCredentials: vi.fn(() => ({
      credentials: [],
      loading: false,
      refresh: vi.fn(),
    })),
    useProviders: vi.fn(),
    useSaveCredential: vi.fn(),
    useDeleteCredential: vi.fn(),
    useTestConnection: vi.fn(),
  })
})

describe('ImproveDialog', () => {
  it('renders when open', () => {
    render(<ImproveDialog {...baseProps} />)
    expect(screen.getByRole('heading', { name: 'Improve formatting' })).toBeInTheDocument()
    // Both the dialog title and the mode badge show "Improve formatting"
    const matches = screen.getAllByText('Improve formatting')
    expect(matches.length).toBeGreaterThanOrEqual(1)
  })

  it('does not render when closed', () => {
    const { container } = render(<ImproveDialog {...baseProps} open={false} />)
    expect(container.querySelector('[role="dialog"]')).not.toBeInTheDocument()
  })

  it('shows the agent select with agent options', () => {
    render(<ImproveDialog {...baseProps} />)
    expect(screen.getByRole('combobox')).toBeInTheDocument()
  })

  it('preselects the persisted agent from generation settings', () => {
    render(<ImproveDialog {...baseProps} />)
    const select = screen.getByRole('combobox') as HTMLSelectElement
    expect(select.value).toBe('agent-1')
  })

  it('preselects the default agent when no persisted agent matches', () => {
    vi.mocked(useGenerationSettings).mockReturnValue({
      settings: { agent_id: '', temperature: 0.7, top_p: 1.0, max_tokens: 1024 },
      setAgent: mockSetAgent,
      update: vi.fn(),
      clearAgent: vi.fn(),
      clearModel: vi.fn(),
    })
    render(<ImproveDialog {...baseProps} />)
    const select = screen.getByRole('combobox') as HTMLSelectElement
    expect(select.value).toBe('agent-1')
  })

  it('Run button is enabled when an agent is selected', () => {
    render(<ImproveDialog {...baseProps} />)
    expect(screen.getByRole('button', { name: /run/i })).not.toBeDisabled()
  })

  it('calls onConfirm with selected agent id when Run is clicked', async () => {
    const user = userEvent.setup()
    render(<ImproveDialog {...baseProps} />)
    await user.click(screen.getByRole('button', { name: /run/i }))
    expect(mockSetAgent).toHaveBeenCalledWith('agent-1')
    expect(mockOnConfirm).toHaveBeenCalledWith('agent-1')
  })

  it('calls onOpenChange(false) when Cancel is clicked', async () => {
    const user = userEvent.setup()
    render(<ImproveDialog {...baseProps} />)
    await user.click(screen.getByRole('button', { name: /cancel/i }))
    expect(mockOnOpenChange).toHaveBeenCalledWith(false)
  })

  it('shows the agent prompt in the info block when present', () => {
    render(<ImproveDialog {...baseProps} />)
    expect(screen.getByText(/You are a scholarly assistant/)).toBeInTheDocument()
  })

  it('shows a loading state while agents are loading', () => {
    vi.mocked(useAgents).mockReturnValue({
      agents: [],
      loading: true,
      refresh: vi.fn(),
    })
    render(<ImproveDialog {...baseProps} />)
    expect(screen.getByText(/Loading agents/)).toBeInTheDocument()
  })

  it('shows an empty state with "Create new agent" when no agents exist', () => {
    vi.mocked(useAgents).mockReturnValue({
      agents: [],
      loading: false,
      refresh: vi.fn(),
    })
    render(<ImproveDialog {...baseProps} />)
    expect(screen.getByText(/No agents configured/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create new agent/i })).toBeInTheDocument()
  })

  it('disables Run and Cancel while isImproving is true', () => {
    render(<ImproveDialog {...baseProps} isImproving={true} />)
    expect(screen.getByRole('button', { name: /run/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeDisabled()
  })

  it('renders custom title when provided', () => {
    render(<ImproveDialog {...baseProps} title="Create optimized document" />)
    expect(screen.getByRole('heading', { name: 'Create optimized document' })).toBeInTheDocument()
  })

  it('renders custom description when provided', () => {
    render(<ImproveDialog {...baseProps} description="Custom description text." />)
    expect(screen.getByText('Custom description text.')).toBeInTheDocument()
  })
})
