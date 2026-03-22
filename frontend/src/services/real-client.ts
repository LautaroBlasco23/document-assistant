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
    const message =
      error.response?.data?.detail ?? error.response?.data?.message ?? error.message ?? 'Server error'
    useAppStore.getState().addError(String(message))
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

  async ingestDocument(formData: FormData): Promise<IngestTaskOut> {
    const res = await httpClient.post<IngestTaskOut>('/documents/ingest', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
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

  async summarizeChapter(chapter: number, bookTitle: string, documentHash: string): Promise<TaskResponseOut> {
    const res = await httpClient.post<TaskResponseOut>('/chapters/summarize', {
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

  async getStoredSummary(docHash: string, chapter: number): Promise<SummaryResponse | null> {
    const res = await httpClient.get<SummaryResponse>(`/documents/${docHash}/summaries/${chapter}`, {
      validateStatus: (s) => s === 200 || s === 404,
    })
    return res.status === 404 ? null : res.data
  }

  async getStoredFlashcards(docHash: string, chapter: number): Promise<FlashcardResponse[]> {
    const res = await httpClient.get<FlashcardResponse[]>(`/documents/${docHash}/flashcards`, {
      params: { chapter },
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
