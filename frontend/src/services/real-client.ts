import axios, { type AxiosInstance, type AxiosError } from 'axios'
import { useAppStore } from '../stores/app-store'
import type {
  HealthOut,
  ConfigOut,
  ModelsOut,
  AgentOut,
  CreateAgentRequest,
  UpdateAgentRequest,
  TaskStatusOut,
  ActiveTasksOut,
  DocumentPreviewOut,
  KnowledgeTreeQuestionType,
  KnowledgeTreeQuestionOut,
  FlashcardOut,
  ChatRequest,
  ChatResponse,
} from '../types/api'
import type { ServiceClient } from './client.interface'
import type { KnowledgeTree, KnowledgeChapter, KnowledgeDocument, ExamSession, CreateExamSessionPayload } from '../types/knowledge-tree'

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
  (error: AxiosError<{ detail?: unknown; message?: string }>) => {
    // Handle 401 - Unauthorized (token expired or invalid)
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
      return Promise.reject(error)
    }

    // Handle 402 - Plan limit exceeded
    if (error.response?.status === 402) {
      const data = error.response?.data
      const detail = data?.detail as { message?: string; resource?: string } | undefined
      const message = detail?.message || 'Plan limit exceeded'
      useAppStore.getState().addError(message)
      return Promise.reject(new Error(message))
    }

    const data = error.response?.data
    let message: string
    if (Array.isArray(data?.detail)) {
      message = data.detail.map((e) => String((e as { msg?: string })?.msg ?? e)).join(', ')
    } else {
      message = String(data?.detail ?? data?.message ?? error.message ?? 'Server error')
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

  async getModels(): Promise<ModelsOut> {
    const res = await httpClient.get<ModelsOut>('/models')
    return res.data
  }

  // Agents
  async listAgents(): Promise<AgentOut[]> {
    const res = await httpClient.get<AgentOut[]>('/agents')
    return res.data
  }

  async createAgent(req: CreateAgentRequest): Promise<AgentOut> {
    const res = await httpClient.post<AgentOut>('/agents', req)
    return res.data
  }

  async updateAgent(id: string, req: UpdateAgentRequest): Promise<AgentOut> {
    const res = await httpClient.put<AgentOut>(`/agents/${id}`, req)
    return res.data
  }

  async deleteAgent(id: string): Promise<void> {
    await httpClient.delete(`/agents/${id}`)
  }

  async getDefaultAgent(): Promise<AgentOut> {
    const res = await httpClient.get<AgentOut>('/agents/default')
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

  getDocumentThumbnailUrl(treeId: string, docId: string): string {
    const token = localStorage.getItem('auth_token')
    return `${baseURL}/knowledge-trees/${treeId}/documents/${docId}/thumbnail?token=${token}`
  }

  async generateFlashcardFromSelection(treeId: string, chapter: number, selectedText: string): Promise<{ task_id: string }> {
    const res = await httpClient.post<{ task_id: string; task_type: string }>(
      `/knowledge-trees/${treeId}/chapters/${chapter}/flashcards`,
      { selected_text: selectedText }
    )
    return res.data
  }

  async draftFlashcard(
    treeId: string,
    chapter: number,
    selectedText: string,
    model?: string,
    agentId?: string,
  ): Promise<{ front: string; back: string; source_text: string }> {
    const res = await httpClient.post<{ front: string; back: string; source_text: string }>(
      `/knowledge-trees/${treeId}/chapters/${chapter}/flashcards/draft`,
      { selected_text: selectedText, model: model ?? null, agent_id: agentId ?? null },
    )
    return res.data
  }

  async saveFlashcard(
    treeId: string,
    chapter: number,
    payload: { front: string; back: string; source_text?: string | null },
  ): Promise<{ id: string }> {
    const res = await httpClient.post<{ id: string }>(
      `/knowledge-trees/${treeId}/chapters/${chapter}/flashcards/save`,
      payload,
    )
    return res.data
  }

  async draftQuestion(
    treeId: string,
    chapter: number,
    questionType: KnowledgeTreeQuestionType,
    selectedText: string,
    model?: string,
    agentId?: string,
  ): Promise<{ question_type: KnowledgeTreeQuestionType; question_data: Record<string, unknown> }> {
    const res = await httpClient.post<{
      question_type: KnowledgeTreeQuestionType
      question_data: Record<string, unknown>
    }>(`/knowledge-trees/${treeId}/chapters/${chapter}/questions/draft`, {
      question_type: questionType,
      selected_text: selectedText,
      model: model ?? null,
      agent_id: agentId ?? null,
    })
    return res.data
  }

  async saveQuestion(
    treeId: string,
    chapter: number,
    questionType: KnowledgeTreeQuestionType,
    questionData: Record<string, unknown>,
  ): Promise<{ id: string }> {
    const res = await httpClient.post<{ id: string }>(
      `/knowledge-trees/${treeId}/chapters/${chapter}/questions/save`,
      { question_type: questionType, question_data: questionData },
    )
    return res.data
  }

  // Knowledge Tree Questions
  async generateKnowledgeTreeQuestions(
    treeId: string,
    chapter: number,
    questionTypes?: KnowledgeTreeQuestionType[],
    model?: string,
    agentId?: string,
    numQuestions?: number | null,
  ): Promise<{ task_id: string }> {
    const body: Record<string, unknown> = questionTypes ? { question_types: questionTypes } : {}
    if (model) body.model = model
    if (agentId) body.agent_id = agentId
    if (numQuestions !== undefined) body.num_questions = numQuestions
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

  async deleteAllKnowledgeTreeQuestions(
    treeId: string,
    chapter: number,
    type?: KnowledgeTreeQuestionType
  ): Promise<void> {
    const params = type ? `?type=${type}` : ''
    await httpClient.delete(
      `/knowledge-trees/${treeId}/chapters/${chapter}/questions${params}`
    )
  }

  async generateChapterFlashcards(
    treeId: string,
    chapter: number,
    numFlashcards?: number | null,
    model?: string,
    agentId?: string,
  ): Promise<{ task_id: string }> {
    const body: Record<string, unknown> = {}
    if (numFlashcards) body.num_flashcards = numFlashcards
    if (model) body.model = model
    if (agentId) body.agent_id = agentId
    const res = await httpClient.post<{ task_id: string }>(
      `/knowledge-trees/${treeId}/chapters/${chapter}/flashcards/generate`,
      body,
    )
    return res.data
  }

  async listChapterFlashcards(treeId: string, chapter: number): Promise<FlashcardOut[]> {
    const res = await httpClient.get<FlashcardOut[]>(
      `/knowledge-trees/${treeId}/chapters/${chapter}/flashcards`
    )
    return res.data
  }

  async deleteKnowledgeTreeFlashcard(treeId: string, chapter: number, flashcardId: string): Promise<void> {
    await httpClient.delete(
      `/knowledge-trees/${treeId}/chapters/${chapter}/flashcards/${flashcardId}`
    )
  }

  async deleteAllKnowledgeTreeFlashcards(treeId: string, chapter: number): Promise<void> {
    await httpClient.delete(
      `/knowledge-trees/${treeId}/chapters/${chapter}/flashcards`
    )
  }

  // Exam Sessions
  async saveExamSession(treeId: string, chapter: number, payload: CreateExamSessionPayload): Promise<ExamSession> {
    const res = await httpClient.post<ExamSession>(
      `/knowledge-trees/${treeId}/chapters/${chapter}/exam-sessions`,
      payload,
    )
    return res.data
  }

  async listExamSessions(treeId: string, chapter: number): Promise<ExamSession[]> {
    const res = await httpClient.get<ExamSession[]>(
      `/knowledge-trees/${treeId}/chapters/${chapter}/exam-sessions`
    )
    return res.data
  }

  async getExamSession(treeId: string, chapter: number, sessionId: string): Promise<ExamSession> {
    const res = await httpClient.get<ExamSession>(
      `/knowledge-trees/${treeId}/chapters/${chapter}/exam-sessions/${sessionId}`
    )
    return res.data
  }

  // Chat
  async chat(request: ChatRequest): Promise<ChatResponse> {
    try {
      const res = await httpClient.post<ChatResponse>('/chat', request)
      return res.data
    } catch (err) {
      const axiosErr = err as import('axios').AxiosError<{ detail?: string; provider?: string; retry_after?: number }>
      if (axiosErr.response?.status === 503) {
        const data = axiosErr.response.data
        if (data?.detail === 'rate_limited') {
          const rateLimitErr = new Error('rate_limited') as Error & { provider: string; retry_after: number }
          rateLimitErr.name = 'RateLimitError'
          rateLimitErr.provider = data.provider ?? 'AI provider'
          rateLimitErr.retry_after = data.retry_after ?? 60
          throw rateLimitErr
        }
      }
      throw err
    }
  }
}
