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
  ExamResultOut,
  ChapterExamStatusOut,
  ChatResponse,
  CreateDocumentRequest,
  CreateDocumentResponse,
  AppendContentResponse,
  DocumentContentResponse,
  UpdateContentResponse,
} from '../types/api'
import type { ServiceClient } from './client.interface'
import type { KnowledgeTree, KnowledgeChapter, KnowledgeDocument } from '../types/knowledge-tree'

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

  async summarizeChapter(chapter: number, chapterIndex: number, bookTitle: string, documentHash: string, force = false): Promise<TaskResponseOut> {
    const res = await httpClient.post<TaskResponseOut>('/chapters/summarize', {
      chapter,
      chapter_index: chapterIndex,
      book_title: bookTitle,
      document_hash: documentHash,
      force,
    })
    return res.data
  }

  async generateFlashcards(chapter: number, chapterIndex: number, bookTitle: string, documentHash: string, force = false): Promise<TaskResponseOut> {
    const res = await httpClient.post<TaskResponseOut>('/chapters/flashcards', {
      chapter,
      chapter_index: chapterIndex,
      book_title: bookTitle,
      document_hash: documentHash,
      force,
    })
    return res.data
  }

  async getStoredSummary(docHash: string, chapter: number, chapterIndex?: number): Promise<SummaryResponse | null> {
    // Use chapter_index if provided (0-based), convert to 1-based for API
    const chapterParam = chapterIndex !== undefined ? chapterIndex + 1 : chapter
    const res = await httpClient.get<SummaryResponse>(`/documents/${docHash}/summaries/${chapterParam}`, {
      validateStatus: (s) => s === 200 || s === 404,
    })
    return res.status === 404 ? null : res.data
  }

  async deleteSummary(docHash: string, chapter: number, chapterIndex?: number): Promise<void> {
    const chapterParam = chapterIndex !== undefined ? chapterIndex + 1 : chapter
    await httpClient.delete(`/documents/${docHash}/summaries/${chapterParam}`)
  }

  async getStoredFlashcards(docHash: string, chapter: number, chapterIndex?: number): Promise<FlashcardResponse[]> {
    // Use chapter_index if provided (0-based), convert to 1-based for API
    const chapterParam = chapterIndex !== undefined ? chapterIndex + 1 : chapter
    const res = await httpClient.get<FlashcardResponse[]>(`/documents/${docHash}/flashcards`, {
      params: { chapter: chapterParam, status: 'approved' },
    })
    return res.data
  }

  async getPendingFlashcards(docHash: string, chapter?: number, chapterIndex?: number): Promise<FlashcardResponse[]> {
    const params: Record<string, unknown> = { status: 'pending' }
    if (chapter !== undefined) {
      params.chapter = chapterIndex !== undefined ? chapterIndex + 1 : chapter
    }
    const res = await httpClient.get<FlashcardResponse[]>(`/documents/${docHash}/flashcards`, {
      params,
    })
    return res.data
  }

  async approveFlashcards(docHash: string, flashcardIds: string[]): Promise<void> {
    await httpClient.patch(`/documents/${docHash}/flashcards/approve`, { flashcard_ids: flashcardIds })
  }

  async rejectFlashcards(docHash: string, flashcardIds: string[]): Promise<void> {
    await httpClient.delete(`/documents/${docHash}/flashcards/reject`, {
      data: { flashcard_ids: flashcardIds },
    })
  }

  async approveAllFlashcards(docHash: string, chapter?: number, chapterIndex?: number): Promise<void> {
    const params: Record<string, unknown> = {}
    if (chapter !== undefined) {
      params.chapter = chapterIndex !== undefined ? chapterIndex + 1 : chapter
    }
    await httpClient.post(`/documents/${docHash}/flashcards/approve-all`, null, { params })
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

  async submitExamResult(docHash: string, chapter: number, totalCards: number, correctCount: number): Promise<ExamResultOut> {
    const res = await httpClient.post<ExamResultOut>('/exams', {
      document_hash: docHash,
      chapter,
      total_cards: totalCards,
      correct_count: correctCount,
    })
    return res.data
  }

  async getExamStatus(docHash: string): Promise<ChapterExamStatusOut[]> {
    const res = await httpClient.get<ChapterExamStatusOut[]>(`/documents/${docHash}/exam-status`)
    return res.data
  }

  async getExamStatusForChapter(docHash: string, chapter: number): Promise<ChapterExamStatusOut> {
    const res = await httpClient.get<ChapterExamStatusOut>(`/documents/${docHash}/exam-status/${chapter}`)
    return res.data
  }

  async chat(
    docHash: string,
    query: string,
    chapter: number | null,
    chapterIndex: number | null,
    history: Array<{ role: 'user' | 'assistant'; content: string }>
  ): Promise<ChatResponse> {
    const res = await httpClient.post<ChatResponse>('/chat', {
      document_hash: docHash,
      chapter,
      chapter_index: chapterIndex,
      query,
      history,
    })
    return res.data
  }

  getDocumentFileUrl(docHash: string): string {
    return `/api/documents/${docHash}/file`
  }

  getChapterPdfUrl(docHash: string, chapter: number): string {
    return `/api/documents/${docHash}/chapters/${chapter}/pdf`
  }

  async createDocument(req: CreateDocumentRequest): Promise<CreateDocumentResponse> {
    const res = await httpClient.post<CreateDocumentResponse>('/documents/create', req)
    return res.data
  }

  async appendContent(docHash: string, content: string): Promise<AppendContentResponse> {
    const res = await httpClient.post<AppendContentResponse>(`/documents/${docHash}/append`, { content })
    return res.data
  }

  async getDocumentContent(docHash: string): Promise<DocumentContentResponse> {
    const res = await httpClient.get<DocumentContentResponse>(`/documents/${docHash}/content`)
    return res.data
  }

  async updateDocumentContent(docHash: string, content: string): Promise<UpdateContentResponse> {
    const res = await httpClient.put<UpdateContentResponse>(`/documents/${docHash}/content`, { content })
    return res.data
  }

  // Knowledge Trees — not yet implemented in backend
  async listKnowledgeTrees(): Promise<KnowledgeTree[]> { return [] }
  async createKnowledgeTree(_title: string, _description?: string): Promise<KnowledgeTree> { throw new Error('Not implemented') }
  async deleteKnowledgeTree(_id: string): Promise<void> { throw new Error('Not implemented') }
  async getKnowledgeTreeChapters(_treeId: string): Promise<KnowledgeChapter[]> { return [] }
  async createKnowledgeChapter(_treeId: string, _title: string): Promise<KnowledgeChapter> { throw new Error('Not implemented') }
  async deleteKnowledgeChapter(_treeId: string, _chapterNumber: number): Promise<void> { throw new Error('Not implemented') }
  async listKnowledgeDocuments(_treeId: string, _chapter?: number | null): Promise<KnowledgeDocument[]> { return [] }
  async createKnowledgeDocument(_treeId: string, _chapter: number | null, _title: string, _content: string, _isMain?: boolean): Promise<KnowledgeDocument> { throw new Error('Not implemented') }
  async updateKnowledgeDocument(_id: string, _title: string, _content: string): Promise<KnowledgeDocument> { throw new Error('Not implemented') }
  async deleteKnowledgeDocument(_id: string): Promise<void> { throw new Error('Not implemented') }
  async ingestFileAsKnowledgeDocument(_treeId: string, _chapter: number, _file: File): Promise<KnowledgeDocument> { throw new Error('Not implemented') }
}
