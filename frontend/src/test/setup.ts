import '@testing-library/jest-dom'
import { vi } from 'vitest'
import React from 'react'

// ---------------------------------------------------------------------------
// Browser APIs missing (or flaky) in jsdom
// ---------------------------------------------------------------------------

class IntersectionObserverMock {
  observe = vi.fn()
  disconnect = vi.fn()
  unobserve = vi.fn()
}

Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  configurable: true,
  value: IntersectionObserverMock,
})

class ResizeObserverMock {
  observe = vi.fn()
  disconnect = vi.fn()
  unobserve = vi.fn()
}

Object.defineProperty(window, 'ResizeObserver', {
  writable: true,
  configurable: true,
  value: ResizeObserverMock,
})

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  configurable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value
    },
    removeItem: (key: string) => {
      delete store[key]
    },
    clear: () => {
      store = {}
    },
    length: 0,
    key: () => null,
  } as Storage
})()

Object.defineProperty(window, 'localStorage', {
  writable: true,
  configurable: true,
  value: localStorageMock,
})

const sessionStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value
    },
    removeItem: (key: string) => {
      delete store[key]
    },
    clear: () => {
      store = {}
    },
    length: 0,
    key: () => null,
  } as Storage
})()

Object.defineProperty(window, 'sessionStorage', {
  writable: true,
  configurable: true,
  value: sessionStorageMock,
})

// ---------------------------------------------------------------------------
// crypto.randomUUID may not exist in jsdom depending on version
// ---------------------------------------------------------------------------

if (
  typeof globalThis.crypto === 'undefined' ||
  typeof globalThis.crypto.randomUUID !== 'function'
) {
  Object.defineProperty(globalThis, 'crypto', {
    writable: true,
    configurable: true,
    value: {
      randomUUID: () => 'test-uuid-' + Math.random().toString(36).slice(2),
      getRandomValues: (arr: Uint8Array) => arr,
      subtle: {} as SubtleCrypto,
    },
  })
}

// ---------------------------------------------------------------------------
// DOMMatrix may be missing in jsdom (required by pdfjs-dist)
// ---------------------------------------------------------------------------

if (typeof globalThis.DOMMatrix === 'undefined') {
  Object.defineProperty(globalThis, 'DOMMatrix', {
    writable: true,
    configurable: true,
    value: class DOMMatrix {
      constructor(init?: any) {}
      multiply() { return this }
      translate() { return this }
      scale() { return this }
    },
  })
}

// ---------------------------------------------------------------------------
// Module mocks — registered before any test imports them
// ---------------------------------------------------------------------------

vi.mock('pdfjs-dist', () => ({
  getDocument: vi.fn(() => ({
    promise: Promise.resolve({
      numPages: 1,
      getPage: vi.fn(() =>
        Promise.resolve({
          getTextContent: vi.fn(() => Promise.resolve({ items: [] })),
        })
      ),
    }),
  })),
  GlobalWorkerOptions: {
    workerSrc: '',
  },
}))

vi.mock('react-pdf', async () => {
  const actual = await vi.importActual<typeof import('react-pdf')>('react-pdf')
  return {
    ...actual,
    pdfjs: {
      GlobalWorkerOptions: { workerSrc: '' },
    },
    Document: ({ children }: { children?: React.ReactNode }) =>
      React.createElement('div', { 'data-testid': 'react-pdf-document' }, children),
    Page: () =>
      React.createElement('div', { 'data-testid': 'react-pdf-page' }, 'Page'),
  }
})

vi.mock('epubjs', () => ({
  default: vi.fn(() => ({
    rendered: { display: vi.fn() },
  })),
}))
