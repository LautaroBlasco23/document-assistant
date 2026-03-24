import axios, { type AxiosInstance } from 'axios'
import { useAppStore } from '../stores/app-store'
import type {
  HealthOut,
  DocumentOut,
  DocumentStructureOut,
  IngestTaskOut,
  ConfigOut,
  TaskStatusOut,
  TaskResponseOut,
  SummaryResponse,
  FlashcardResponse,
  MetadataResponse,
  ChapterDeleteResponse,
  ActiveTasksOut,
  DocumentPreviewOut,
} from '../types/api'
import type { ServiceClient } from './client.interface'

const httpClient: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

httpClient.interceptors.response.use(
  (res) => res,
  (error) => {
    const data = error.response?.data
    let message: string
    if (Array.isArray(data?.detail)) {
      message = data.detail.map((e: { msg: string }) => e.msg).join(', ')
    } else {
      message = data?.detail ?? data?.message ?? error.message ?? 'Server error'
    }
    useAppStore.getState().addError(message)
    return Promise.reject(error)
  }
)

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

  async deleteChapter(docHash: string, chapterNumber: number): Promise<ChapterDeleteResponse> {
    const res = await httpClient.delete<ChapterDeleteResponse>(
      `/documents/${docHash}/chapters/${chapterNumber}`
    )
    return res.data
  }

  async ingestDocument(formData: FormData): Promise<IngestTaskOut> {
    const res = await httpClient.post<IngestTaskOut>('/documents/ingest', formData, {
      headers: {
        'Content-Type': undefined,
      },
    })
    return res.data
  }

  async previewDocument(file: File): Promise<DocumentPreviewOut> {
    const formData = new FormData()
    formData.append('file', file)
    const res = await httpClient.post<DocumentPreviewOut>('/documents/preview', formData, {
      headers: {
        'Content-Type': undefined,
      },
    })
    return res.data
  }

  async ingestDocumentChapters(
    fileHash: string,
    file: File,
    chapterIndices: number[],
    documentType = '',
    description = ''
  ): Promise<IngestTaskOut> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('chapter_indices', JSON.stringify(chapterIndices))
    formData.append('document_type', documentType)
    formData.append('description', description)
    const res = await httpClient.post<IngestTaskOut>(
      `/documents/${fileHash}/ingest`,
      formData,
      {
        headers: {
          'Content-Type': undefined,
        },
      }
    )
    return res.data
  }

  async getConfig(): Promise<ConfigOut> {
    const res = await httpClient.get<ConfigOut>('/config')
    return res.data
  }

  async getTaskStatus(taskId: string): Promise<TaskStatusOut> {
    const res = await httpClient.get<TaskStatusOut>(`/tasks/${taskId}`)
    return res.data
  }

  async listActiveTasks(): Promise<ActiveTasksOut> {
    const res = await httpClient.get<ActiveTasksOut>('/tasks/active')
    return res.data
  }

  async summarizeChapter(chapter: number, qdrantIndex: number, bookTitle: string, documentHash: string, force = false): Promise<TaskResponseOut> {
    const res = await httpClient.post<TaskResponseOut>('/chapters/summarize', {
      chapter,
      qdrant_index: qdrantIndex,
      book_title: bookTitle,
      document_hash: documentHash,
      force,
    })
    return res.data
  }

  async generateFlashcards(chapter: number, qdrantIndex: number, bookTitle: string, documentHash: string, force = false): Promise<TaskResponseOut> {
    const res = await httpClient.post<TaskResponseOut>('/chapters/flashcards', {
      chapter,
      qdrant_index: qdrantIndex,
      book_title: bookTitle,
      document_hash: documentHash,
      force,
    })
    return res.data
  }

  async getStoredSummary(docHash: string, chapter: number, qdrantIndex?: number): Promise<SummaryResponse | null> {
    // Use qdrant_index if provided, otherwise fall back to chapter-1
    const chapterParam = qdrantIndex !== undefined ? qdrantIndex + 1 : chapter
    const res = await httpClient.get<SummaryResponse>(`/documents/${docHash}/summaries/${chapterParam}`, {
      validateStatus: (s) => s === 200 || s === 404,
    })
    return res.status === 404 ? null : res.data
  }

  async deleteSummary(docHash: string, chapter: number, qdrantIndex?: number): Promise<void> {
    const chapterParam = qdrantIndex !== undefined ? qdrantIndex + 1 : chapter
    await httpClient.delete(`/documents/${docHash}/summaries/${chapterParam}`)
  }

  async getStoredFlashcards(docHash: string, chapter: number, qdrantIndex?: number): Promise<FlashcardResponse[]> {
    // Use qdrant_index if provided, otherwise fall back to chapter-1
    const chapterParam = qdrantIndex !== undefined ? qdrantIndex + 1 : chapter
    const res = await httpClient.get<FlashcardResponse[]>(`/documents/${docHash}/flashcards`, {
      params: { chapter: chapterParam },
    })
    return res.data
  }

  async getMetadata(docHash: string): Promise<MetadataResponse> {
    const res = await httpClient.get<MetadataResponse>(`/documents/${docHash}/metadata`)
    return res.data
  }

  async saveMetadata(docHash: string, description: string, documentType = ''): Promise<MetadataResponse> {
    const res = await httpClient.put<MetadataResponse>(`/documents/${docHash}/metadata`, {
      description,
      document_type: documentType,
    })
    return res.data
  }
}
