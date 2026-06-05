/**
 * Subject: src/stores/reader-preferences.ts — useReaderPreferences
 * Scope:   load defaults, update partial preferences, localStorage persistence
 * Out of scope:
 *   - UI rendering of reader settings → component tests
 * Setup:   Store state is reset before each test; localStorage is mocked.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { useReaderPreferences, load } from './reader-preferences'

describe('useReaderPreferences', () => {
  beforeEach(() => {
    localStorage.clear()
    useReaderPreferences.setState({
      preferences: { defaultShowLeft: true, defaultShowRight: true, contentWidth: 'comfortable' },
    })
  })

  it('loads default preferences when nothing is stored', () => {
    const prefs = useReaderPreferences.getState().preferences

    expect(prefs.defaultShowLeft).toBe(true)
    expect(prefs.defaultShowRight).toBe(true)
    expect(prefs.contentWidth).toBe('comfortable')
  })

  it('update merges partial preferences', () => {
    useReaderPreferences.getState().update({ contentWidth: 'wide' })

    const prefs = useReaderPreferences.getState().preferences
    expect(prefs.contentWidth).toBe('wide')
    expect(prefs.defaultShowLeft).toBe(true)
    expect(prefs.defaultShowRight).toBe(true)
  })

  it('update persists to localStorage', () => {
    useReaderPreferences.getState().update({ defaultShowLeft: false })

    const stored = JSON.parse(localStorage.getItem('docassist_reader_preferences') || '{}')
    expect(stored.defaultShowLeft).toBe(false)
    expect(stored.contentWidth).toBe('comfortable')
  })

  it('update can change all fields at once', () => {
    useReaderPreferences.getState().update({
      defaultShowLeft: false,
      defaultShowRight: false,
      contentWidth: 'full',
    })

    const prefs = useReaderPreferences.getState().preferences
    expect(prefs.defaultShowLeft).toBe(false)
    expect(prefs.defaultShowRight).toBe(false)
    expect(prefs.contentWidth).toBe('full')
  })

  it('load returns parsed data when localStorage has all fields', () => {
    localStorage.setItem('docassist_reader_preferences', JSON.stringify({
      defaultShowLeft: false, defaultShowRight: true, contentWidth: 'wide',
    }))

    const result = load()
    expect(result.defaultShowLeft).toBe(false)
    expect(result.defaultShowRight).toBe(true)
    expect(result.contentWidth).toBe('wide')
  })

  it('load merges defaults when localStorage has partial data', () => {
    // Only store defaultShowLeft — the rest should fall back to defaults.
    localStorage.setItem('docassist_reader_preferences', JSON.stringify({
      defaultShowLeft: false,
    }))

    const result = load()
    expect(result.defaultShowLeft).toBe(false)
    expect(result.defaultShowRight).toBe(true)
    expect(result.contentWidth).toBe('comfortable')
  })

  it('load returns full defaults when localStorage is empty', () => {
    const result = load()
    expect(result.defaultShowLeft).toBe(true)
    expect(result.defaultShowRight).toBe(true)
    expect(result.contentWidth).toBe('comfortable')
  })

  it('load returns full defaults on corrupt JSON', () => {
    localStorage.setItem('docassist_reader_preferences', 'not json')
    const result = load()
    expect(result.defaultShowLeft).toBe(true)
    expect(result.defaultShowRight).toBe(true)
    expect(result.contentWidth).toBe('comfortable')
  })
})
