import { create } from 'zustand'

export interface Highlight {
  id: string
  text: string
  createdAt: string
  chapterNumber?: number
  pageNumber?: number
  startOffset?: number
  endOffset?: number
}

interface HighlightsState {
  // sourceDocId → visual highlights list
  highlights: Record<string, Highlight[]>
  // sourceDocId → knowledge-document id that stores the highlights
  highlightDocIds: Record<string, string>
  add: (docId: string, text: string, opts?: Partial<Pick<Highlight, 'chapterNumber' | 'pageNumber' | 'startOffset' | 'endOffset'>>) => Highlight
  remove: (docId: string, id: string) => void
  clear: (docId: string) => void
  setHighlightDocId: (sourceDocId: string, highlightsDocId: string) => void
  clearHighlightDocId: (sourceDocId: string) => void
}

function makeId() {
  return `h-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`
}

function load(): Pick<HighlightsState, 'highlights' | 'highlightDocIds'> {
  try {
    const raw = localStorage.getItem('docassist_highlights')
    if (raw) {
      const parsed = JSON.parse(raw)
      return {
        highlights: (parsed && typeof parsed.highlights === 'object' && parsed.highlights !== null)
          ? parsed.highlights
          : {},
        highlightDocIds: (parsed && typeof parsed.highlightDocIds === 'object' && parsed.highlightDocIds !== null)
          ? parsed.highlightDocIds
          : {},
      }
    }
  } catch { /* ignore */ }
  return { highlights: {}, highlightDocIds: {} }
}

function persist(state: Pick<HighlightsState, 'highlights' | 'highlightDocIds'>) {
  try {
    localStorage.setItem('docassist_highlights', JSON.stringify(state))
  } catch { /* ignore */ }
}

export const useHighlights = create<HighlightsState>((set, get) => ({
  ...load(),
  add: (docId, text, opts?) => {
    const highlight: Highlight = { id: makeId(), text, createdAt: new Date().toISOString(), ...opts }
    const next = { highlights: { ...get().highlights, [docId]: [...(get().highlights[docId] ?? []), highlight] }, highlightDocIds: get().highlightDocIds }
    set(next)
    persist(next)
    return highlight
  },
  remove: (docId, id) => {
    const next = { highlights: { ...get().highlights, [docId]: (get().highlights[docId] ?? []).filter((h) => h.id !== id) }, highlightDocIds: get().highlightDocIds }
    set(next)
    persist(next)
  },
  clear: (docId) => {
    const next = { highlights: { ...get().highlights, [docId]: [] }, highlightDocIds: get().highlightDocIds }
    set(next)
    persist(next)
  },
  setHighlightDocId: (sourceDocId, highlightsDocId) => {
    const next = { highlights: get().highlights ?? {}, highlightDocIds: { ...(get().highlightDocIds ?? {}), [sourceDocId]: highlightsDocId } }
    set(next)
    persist(next)
  },
  clearHighlightDocId: (sourceDocId) => {
    const { [sourceDocId]: _, ...rest } = (get().highlightDocIds ?? {})
    const next = { highlights: get().highlights ?? {}, highlightDocIds: rest }
    set(next)
    persist(next)
  },
}))
