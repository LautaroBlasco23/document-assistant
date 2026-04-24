import axios, { type AxiosInstance, type AxiosError } from 'axios'
import { useAppStore } from '../stores/app-store'
import type {
  HealthOut,
  ConfigOut,
  TaskStatusOut,
  ActiveTasksOut,
  DocumentPreviewOut,
  KnowledgeTreeQuestionType,
  KnowledgeTreeQuestionOut,
} from '../types/api'
import type { ServiceClient } from './client.interface'
import type { KnowledgeTree, KnowledgeChapter, KnowledgeDocument } from '../types/knowledge-tree'

// Detect if running in Electron
const isElectron = typeof window !== 'undefined' && !!(window as Window & { desktopAPI?: unknown }).desktopAPI

// Determine the base URL for API calls
// In Electron production, use full URL since we're served from file://
// In dev (Vite dev server), use relative URL which gets proxied
const baseURL = isElectron ? 'http://127.0.0.1:8000/api' : '/api'

const httpClient: AxiosInstance = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
httpClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Handle auth errors and plan limits
httpClient.interceptors.response.use(
  (res) => res,
  (error: AxiosError) => {
    // Handle 401 - Unauthorized (token expired or invalid)
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
      return Promise.reject(error)
    }

    // Handle 402 - Plan limit exceeded
    if (error.response?.status === 402) {
      const data = error.response?.data as { detail?: { message?: string; resource?: string } }
      const message = data?.detail?.message || 'Plan limit exceeded'
      useAppStore.getState().addError(message)
      return Promise.reject(new Error(message))
    }

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

  // Knowledge Trees
  async listKnowledgeTrees(): Promise<KnowledgeTree[]> {
    const res = await httpClient.get<KnowledgeTree[]>('/knowledge-trees')
    return res.data
  }

  async createKnowledgeTree(title: string, description?: string): Promise<KnowledgeTree> {
    const res = await httpClient.post<KnowledgeTree>('/knowledge-trees', { title, description })
    return res.data
  }

  async updateKnowledgeTree(id: string, title: string, description?: string): Promise<KnowledgeTree> {
    const res = await httpClient.put<KnowledgeTree>(`/knowledge-trees/${id}`, { title, description })
    return res.data
  }

  async deleteKnowledgeTree(id: string): Promise<void> {
    await httpClient.delete(`/knowledge-trees/${id}`)
  }

  async getKnowledgeTreeChapters(treeId: string): Promise<KnowledgeChapter[]> {
    const res = await httpClient.get<KnowledgeChapter[]>(`/knowledge-trees/${treeId}/chapters`)
    return res.data
  }

  async createKnowledgeChapter(treeId: string, title: string): Promise<KnowledgeChapter> {
    const res = await httpClient.post<KnowledgeChapter>(
      `/knowledge-trees/${treeId}/chapters`,
      { title }
    )
    return res.data
  }

  async updateKnowledgeChapter(treeId: string, chapterNumber: number, title: string): Promise<KnowledgeChapter> {
    const res = await httpClient.put<KnowledgeChapter>(
      `/knowledge-trees/${treeId}/chapters/${chapterNumber}`,
      { title }
    )
    return res.data
  }

  async deleteKnowledgeChapter(treeId: string, chapterNumber: number): Promise<void> {
    await httpClient.delete(`/knowledge-trees/${treeId}/chapters/${chapterNumber}`)
  }

  async listKnowledgeDocuments(treeId: string, chapterId?: string | null): Promise<KnowledgeDocument[]> {
    const params: Record<string, unknown> = {}
    if (chapterId !== undefined && chapterId !== null) {
      params.chapter_id = chapterId
    }
    const res = await httpClient.get<KnowledgeDocument[]>(
      `/knowledge-trees/${treeId}/documents`,
      { params }
    )
    return res.data
  }

  async createKnowledgeDocument(
    treeId: string,
    chapterId: string | null,
    title: string,
    content: string,
    isMain = false
  ): Promise<KnowledgeDocument> {
    const res = await httpClient.post<KnowledgeDocument>(
      `/knowledge-trees/${treeId}/documents`,
      { title, content, chapter_id: chapterId, is_main: isMain }
    )
    return res.data
  }

  async updateKnowledgeDocument(id: string, title: string, content: string): Promise<KnowledgeDocument> {
    const res = await httpClient.put<KnowledgeDocument>(
      `/knowledge-trees/_/documents/${id}`,
      { title, content }
    )
    return res.data
  }

  async deleteKnowledgeDocument(id: string): Promise<void> {
    await httpClient.delete(`/knowledge-trees/_/documents/${id}`)
  }

  async previewKnowledgeTreeFile(file: File): Promise<DocumentPreviewOut> {
    const formData = new FormData()
    formData.append('file', file)
    const res = await httpClient.post<DocumentPreviewOut>('/knowledge-trees/preview', formData, {
      headers: { 'Content-Type': undefined },
    })
    return res.data
  }

  async createKnowledgeTreeFromFile(file: File, title?: string, chapterIndices?: number[]): Promise<{ task_id: string }> {
    const formData = new FormData()
    formData.append('file', file)
    if (title) {
      formData.append('title', title)
    }
    if (chapterIndices !== undefined && chapterIndices.length > 0) {
      formData.append('chapter_indices', chapterIndices.join(','))
    }
    const res = await httpClient.post<{ task_id: string; filename: string }>(
      '/knowledge-trees/import',
      formData,
      { headers: { 'Content-Type': undefined } }
    )
    return { task_id: res.data.task_id }
  }

  async ingestFileAsKnowledgeDocument(treeId: string, chapter: number, file: File): Promise<{ task_id: string }> {
    const formData = new FormData()
    formData.append('file', file)
    const res = await httpClient.post<{ task_id: string; filename: string }>(
      `/knowledge-trees/${treeId}/chapters/${chapter}/documents/ingest`,
      formData,
      { headers: { 'Content-Type': undefined } }
    )
    return { task_id: res.data.task_id }
  }

  // Document Reader
  getDocumentFileUrl(treeId: string, docId: string): string {
    const token = localStorage.getItem('auth_token')
    return `${baseURL}/knowledge-trees/${treeId}/documents/${docId}/file?token=${token}`
  }

  async generateFlashcardFromSelection(treeId: string, chapter: number, selectedText: string): Promise<{ task_id: string }> {
    const res = await httpClient.post<{ task_id: string; task_type: string }>(
      `/knowledge-trees/${treeId}/chapters/${chapter}/flashcards`,
      { selected_text: selectedText }
    )
    return res.data
  }

  // Knowledge Tree Questions
  async generateKnowledgeTreeQuestions(
    treeId: string,
    chapter: number,
    questionTypes?: KnowledgeTreeQuestionType[]
  ): Promise<{ task_id: string }> {
    const body = questionTypes ? { question_types: questionTypes } : {}
    const res = await httpClient.post<{ task_id: string }>(
      `/knowledge-trees/${treeId}/chapters/${chapter}/questions`,
      body
    )
    return res.data
  }

  async getKnowledgeTreeQuestions(
    treeId: string,
    chapter: number,
    type?: KnowledgeTreeQuestionType
  ): Promise<KnowledgeTreeQuestionOut[]> {
    const params = type ? `?type=${type}` : ''
    const res = await httpClient.get<KnowledgeTreeQuestionOut[]>(
      `/knowledge-trees/${treeId}/chapters/${chapter}/questions${params}`
    )
    return res.data
  }

  async deleteKnowledgeTreeQuestion(
    treeId: string,
    chapter: number,
    questionId: string
  ): Promise<void> {
    await httpClient.delete(
      `/knowledge-trees/${treeId}/chapters/${chapter}/questions/${questionId}`
    )
  }
}
