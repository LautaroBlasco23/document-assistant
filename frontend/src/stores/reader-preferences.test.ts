/**
 * Subject: src/stores/reader-preferences.ts — useReaderPreferences
 * Scope:   load defaults, update partial preferences, localStorage persistence
 * Out of scope:
 *   - UI rendering of reader settings → component tests
 * Setup:   Store state is reset before each test; localStorage is mocked.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import {
  useReaderPreferences,
  load,
  clampFontScale,
  clampContentWidthPx,
  MIN_FONT_SCALE,
  MAX_FONT_SCALE,
  MIN_CONTENT_WIDTH_PX,
  MAX_CONTENT_WIDTH_PX,
} from './reader-preferences'

const DEFAULTS = {
  defaultShowLeft: true,
  defaultShowRight: true,
  contentWidth: 'comfortable' as const,
  fontScale: 1,
  contentWidthPx: null,
}

describe('useReaderPreferences', () => {
  beforeEach(() => {
    localStorage.clear()
    useReaderPreferences.setState({
      preferences: { ...DEFAULTS },
    })
  })

  it('loads default preferences when nothing is stored', () => {
    const prefs = useReaderPreferences.getState().preferences
    expect(prefs.defaultShowLeft).toBe(true)
    expect(prefs.defaultShowRight).toBe(true)
    expect(prefs.contentWidth).toBe('comfortable')
    expect(prefs.fontScale).toBe(1)
    expect(prefs.contentWidthPx).toBeNull()
  })

  it('update merges partial preferences', () => {
    useReaderPreferences.getState().update({ contentWidth: 'wide' })
    const prefs = useReaderPreferences.getState().preferences
    expect(prefs.contentWidth).toBe('wide')
    expect(prefs.defaultShowLeft).toBe(true)
    expect(prefs.fontScale).toBe(1)
  })

  it('update persists to localStorage', () => {
    useReaderPreferences.getState().update({ defaultShowLeft: false })
    const stored = JSON.parse(localStorage.getItem('docassist_reader_preferences') || '{}')
    expect(stored.defaultShowLeft).toBe(false)
    expect(stored.contentWidth).toBe('comfortable')
  })

  it('update can change all base fields at once', () => {
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

  it('update persists fontScale and contentWidthPx', () => {
    useReaderPreferences.getState().update({ fontScale: 1.5, contentWidthPx: 800 })
    const prefs = useReaderPreferences.getState().preferences
    expect(prefs.fontScale).toBe(1.5)
    expect(prefs.contentWidthPx).toBe(800)

    const stored = JSON.parse(localStorage.getItem('docassist_reader_preferences') || '{}')
    expect(stored.fontScale).toBe(1.5)
    expect(stored.contentWidthPx).toBe(800)
  })

  it('load returns parsed data when localStorage has all fields', () => {
    localStorage.setItem('docassist_reader_preferences', JSON.stringify({
      defaultShowLeft: false, defaultShowRight: true, contentWidth: 'wide', fontScale: 1.25, contentWidthPx: 600,
    }))
    const result = load()
    expect(result.defaultShowLeft).toBe(false)
    expect(result.defaultShowRight).toBe(true)
    expect(result.contentWidth).toBe('wide')
    expect(result.fontScale).toBe(1.25)
    expect(result.contentWidthPx).toBe(600)
  })

  it('load merges defaults when localStorage has partial data', () => {
    localStorage.setItem('docassist_reader_preferences', JSON.stringify({ defaultShowLeft: false }))
    const result = load()
    expect(result.defaultShowLeft).toBe(false)
    expect(result.defaultShowRight).toBe(true)
    expect(result.contentWidth).toBe('comfortable')
    expect(result.fontScale).toBe(1)
    expect(result.contentWidthPx).toBeNull()
  })

  it('load returns full defaults when localStorage is empty', () => {
    const result = load()
    expect(result.defaultShowLeft).toBe(true)
    expect(result.defaultShowRight).toBe(true)
    expect(result.contentWidth).toBe('comfortable')
    expect(result.fontScale).toBe(1)
    expect(result.contentWidthPx).toBeNull()
  })

  it('load returns full defaults on corrupt JSON', () => {
    localStorage.setItem('docassist_reader_preferences', 'not json')
    const result = load()
    expect(result.defaultShowLeft).toBe(true)
    expect(result.defaultShowRight).toBe(true)
    expect(result.contentWidth).toBe('comfortable')
    expect(result.fontScale).toBe(1)
    expect(result.contentWidthPx).toBeNull()
  })
})

describe('clampFontScale', () => {
  it('returns the value when within bounds', () => {
    expect(clampFontScale(1)).toBe(1)
    expect(clampFontScale(1.5)).toBe(1.5)
    expect(clampFontScale(MIN_FONT_SCALE)).toBe(MIN_FONT_SCALE)
    expect(clampFontScale(MAX_FONT_SCALE)).toBe(MAX_FONT_SCALE)
  })

  it('clamps below minimum', () => {
    expect(clampFontScale(0.1)).toBe(MIN_FONT_SCALE)
  })

  it('clamps above maximum', () => {
    expect(clampFontScale(5)).toBe(MAX_FONT_SCALE)
  })

  it('returns 1 for NaN', () => {
    expect(clampFontScale(NaN)).toBe(1)
  })

  it('returns 1 for Infinity', () => {
    expect(clampFontScale(Infinity)).toBe(1)
  })
})

describe('clampContentWidthPx', () => {
  it('returns the value when within bounds', () => {
    expect(clampContentWidthPx(800)).toBe(800)
    expect(clampContentWidthPx(MIN_CONTENT_WIDTH_PX)).toBe(MIN_CONTENT_WIDTH_PX)
    expect(clampContentWidthPx(MAX_CONTENT_WIDTH_PX)).toBe(MAX_CONTENT_WIDTH_PX)
  })

  it('clamps below minimum', () => {
    expect(clampContentWidthPx(100)).toBe(MIN_CONTENT_WIDTH_PX)
  })

  it('clamps above maximum', () => {
    expect(clampContentWidthPx(5000)).toBe(MAX_CONTENT_WIDTH_PX)
  })

  it('returns null for NaN', () => {
    expect(clampContentWidthPx(NaN)).toBeNull()
  })

  it('returns null for null', () => {
    expect(clampContentWidthPx(null)).toBeNull()
  })

  it('returns null for undefined', () => {
    expect(clampContentWidthPx(undefined)).toBeNull()
  })
})
