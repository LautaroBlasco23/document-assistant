/**
 * Subject: src/lib/cn.ts — cn
 * Scope:   Combining and deduplicating Tailwind CSS class strings.
 * Out of scope:
 *   - clsx internals                → third-party library
 *   - tailwind-merge internals      → third-party library
 * Setup:   None; pure function.
 */

import { describe, it, expect } from 'vitest'
import { cn } from './cn'

describe('cn', () => {
  // A lone class string should pass through unchanged.
  it('returns a single class unchanged', () => {
    expect(cn('bg-red-500')).toBe('bg-red-500')
  })

  // Multiple class strings are joined with a single space.
  it('joins multiple classes with a space', () => {
    expect(cn('bg-red-500', 'text-white')).toBe('bg-red-500 text-white')
  })

  // Object syntax lets callers toggle classes conditionally; falsy values are omitted.
  it('includes keys with truthy values and excludes falsy ones from an object', () => {
    expect(cn('base', { active: true, disabled: false })).toBe('base active')
  })

  // tailwind-merge resolves conflicting utility classes by keeping the last declaration.
  it('resolves Tailwind conflicts by keeping the last value', () => {
    expect(cn('p-4 p-2')).toBe('p-2')
  })

  // Edge cases: no arguments, undefined, null, and empty strings are all handled silently.
  it('handles empty, undefined, and null inputs gracefully', () => {
    expect(cn()).toBe('')
    expect(cn(undefined)).toBe('')
    expect(cn(null)).toBe('')
    expect(cn('')).toBe('')
    expect(cn('a', undefined, 'b', null, '', 'c')).toBe('a b c')
  })
})
