/**
 * Subject: src/stores/generation-settings.ts — useGenerationSettings
 * Scope:   load defaults, update, setAgent, clearAgent, clearModel, localStorage persistence
 * Out of scope:
 *   - API interactions with agents → knowledge-tree-store tests
 * Setup:   Store state is reset before each test; localStorage is mocked.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { useGenerationSettings } from './generation-settings'

describe('useGenerationSettings', () => {
  beforeEach(() => {
    localStorage.clear()
    useGenerationSettings.setState({
      settings: { temperature: 0.7, top_p: 1.0, max_tokens: 1024 },
    })
  })

  it('loads default settings when nothing is stored', () => {
    const settings = useGenerationSettings.getState().settings

    expect(settings.temperature).toBe(0.7)
    expect(settings.top_p).toBe(1.0)
    expect(settings.max_tokens).toBe(1024)
  })

  it('update merges partial settings', () => {
    useGenerationSettings.getState().update({ temperature: 0.9 })

    const settings = useGenerationSettings.getState().settings
    expect(settings.temperature).toBe(0.9)
    expect(settings.top_p).toBe(1.0)
    expect(settings.max_tokens).toBe(1024)
  })

  it('update persists to localStorage', () => {
    useGenerationSettings.getState().update({ max_tokens: 2048 })

    const stored = JSON.parse(localStorage.getItem('docassist_generation_settings') || '{}')
    expect(stored.max_tokens).toBe(2048)
    expect(stored.temperature).toBe(0.7)
  })

  it('setAgent adds agent_id to settings', () => {
    useGenerationSettings.getState().setAgent('agent-123')

    const settings = useGenerationSettings.getState().settings
    expect(settings.agent_id).toBe('agent-123')
  })

  it('setAgent persists to localStorage', () => {
    useGenerationSettings.getState().setAgent('agent-123')

    const stored = JSON.parse(localStorage.getItem('docassist_generation_settings') || '{}')
    expect(stored.agent_id).toBe('agent-123')
  })

  it('clearAgent removes agent_id from settings', () => {
    useGenerationSettings.getState().setAgent('agent-123')
    useGenerationSettings.getState().clearAgent()

    const settings = useGenerationSettings.getState().settings
    expect(settings.agent_id).toBeUndefined()
    expect(settings.temperature).toBe(0.7)
  })

  it('clearAgent persists to localStorage', () => {
    useGenerationSettings.getState().setAgent('agent-123')
    useGenerationSettings.getState().clearAgent()

    const stored = JSON.parse(localStorage.getItem('docassist_generation_settings') || '{}')
    expect(stored.agent_id).toBeUndefined()
  })

  it('clearModel removes model from settings', () => {
    useGenerationSettings.getState().update({ model: 'gpt-4' })
    useGenerationSettings.getState().clearModel()

    const settings = useGenerationSettings.getState().settings
    expect(settings.model).toBeUndefined()
    expect(settings.temperature).toBe(0.7)
  })

  it('clearModel persists to localStorage', () => {
    useGenerationSettings.getState().update({ model: 'gpt-4' })
    useGenerationSettings.getState().clearModel()

    const stored = JSON.parse(localStorage.getItem('docassist_generation_settings') || '{}')
    expect(stored.model).toBeUndefined()
  })

  it('handles corrupt localStorage gracefully', () => {
    localStorage.setItem('docassist_generation_settings', 'not json')

    // Should not throw — defaults are used
    const settings = useGenerationSettings.getState().settings
    expect(settings).toBeDefined()
  })
})
