/**
 * Subject: src/lib/pdf-text.ts — extractPdfText
 * Scope:   Extracting text from PDF documents via pdfjs.
 * Out of scope:
 *   - react-pdf component rendering   → component tests
 *   - Real PDF binary parsing         → we mock pdfjs entirely
 * Setup:   react-pdf / pdfjs is mocked to return synthetic page text.
 */

import { describe, it, expect, vi } from 'vitest'
import { extractPdfText } from './pdf-text'

// Override the setup-file react-pdf mock with a getDocument implementation.
vi.mock('react-pdf', () => ({
  pdfjs: {
    getDocument: vi.fn(),
    GlobalWorkerOptions: { workerSrc: '' },
  },
}))

import { pdfjs } from 'react-pdf'

function mockPdfPages(pages: string[]) {
  const getPage = vi.fn().mockImplementation((pageNum: number) => {
    const text = pages[pageNum - 1] ?? ''
    return Promise.resolve({
      getTextContent: () =>
        Promise.resolve({
          items: text.split(' ').map((str) => ({ str })),
        }),
    })
  })

  vi.mocked(pdfjs.getDocument).mockReturnValue({
    promise: Promise.resolve({
      numPages: pages.length,
      getPage,
    }),
  } as any)
}

describe('extractPdfText', () => {
  // Concatenates text from multiple pages with double newline separators.
  it('concatenates text from multiple pages separated by double newlines', async () => {
    mockPdfPages(['Page one text here', 'Page two text here'])
    const result = await extractPdfText('dummy-url')
    expect(result).toBe('Page one text here\n\nPage two text here')
  })

  // An empty PDF (zero pages) yields an empty string.
  it('returns an empty string for an empty PDF', async () => {
    mockPdfPages([])
    const result = await extractPdfText('dummy-url')
    expect(result).toBe('')
  })

  // A single-page PDF returns exactly that page's text.
  it('returns the text of a single-page PDF', async () => {
    mockPdfPages(['Only page content'])
    const result = await extractPdfText('dummy-url')
    expect(result).toBe('Only page content')
  })
})
