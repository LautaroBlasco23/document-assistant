import axios, { type AxiosInstance } from 'axios'
import { streamSSE } from '../lib/sse'
import type {
  HealthOut,
  DocumentOut,
  DocumentStructureOut,
  IngestTaskOut,
  SearchResultsOut,
  ConfigOut,
  TaskStatusOut,
  TaskResponseOut,
} from '../types/api'
import type { SSEEvent } from '../types/domain'
import type { ServiceClient } from './client.interface'

const httpClient: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export class RealClient implements ServiceClient {
  async health(): Promise<HealthOut> {
    const res = await httpClient.get<HealthOut>('/health')
    return res.data
  }

  async listDocuments(): Promise<DocumentOut[]> {
    const res = await httpClient.get<DocumentOut[]>('/documents')
    return res.data
  }

  async documentStructure(hash: string): Promise<DocumentStructureOut> {
    const res = await httpClient.get<DocumentStructureOut>(`/documents/${hash}/structure`)
    return res.data
  }

  async deleteDocument(hash: string): Promise<void> {
    await httpClient.delete(`/documents/${hash}`)
  }

  async ingestDocument(formData: FormData): Promise<IngestTaskOut> {
    const res = await httpClient.post<IngestTaskOut>('/documents/ingest', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return res.data
  }

  async search(query: string, k: number = 5, chapter?: number, book?: string): Promise<SearchResultsOut> {
    const res = await httpClient.post<SearchResultsOut>('/search', { query, k, chapter, book })
    return res.data
  }

  async streamAsk(
    query: string,
    chapter: number | undefined,
    onEvent: (event: SSEEvent) => void
  ): Promise<void> {
    const body: Record<string, unknown> = { query }
    if (chapter !== undefined) {
      body.chapter = chapter
    }
    await streamSSE('/api/ask', 'POST', body, onEvent)
  }

  async getConfig(): Promise<ConfigOut> {
    const res = await httpClient.get<ConfigOut>('/config')
    return res.data
  }

  async getTaskStatus(taskId: string): Promise<TaskStatusOut> {
    const res = await httpClient.get<TaskStatusOut>(`/tasks/${taskId}`)
    return res.data
  }

  async summarizeChapter(chapter: number, bookTitle: string, documentHash: string): Promise<TaskResponseOut> {
    const res = await httpClient.post<TaskResponseOut>('/chapters/summarize', {
      chapter,
      book_title: bookTitle,
      document_hash: documentHash,
    })
    return res.data
  }

  async generateQA(chapter: number, bookTitle: string, documentHash: string): Promise<TaskResponseOut> {
    const res = await httpClient.post<TaskResponseOut>('/chapters/questions', {
      chapter,
      book_title: bookTitle,
      document_hash: documentHash,
    })
    return res.data
  }

  async generateFlashcards(chapter: number, bookTitle: string, documentHash: string): Promise<TaskResponseOut> {
    const res = await httpClient.post<TaskResponseOut>('/chapters/flashcards', {
      chapter,
      book_title: bookTitle,
      document_hash: documentHash,
    })
    return res.data
  }
}
