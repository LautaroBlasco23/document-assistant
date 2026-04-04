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

export interface ServiceClient {
  health(): Promise<HealthOut>
  listDocuments(): Promise<DocumentOut[]>
  documentStructure(hash: string): Promise<DocumentStructureOut>
  deleteDocument(hash: string): Promise<void>
  deleteChapter(docHash: string, chapterNumber: number): Promise<ChapterDeleteResponse>
  ingestDocument(formData: FormData): Promise<IngestTaskOut>
  previewDocument(file: File): Promise<DocumentPreviewOut>
  ingestDocumentChapters(
    fileHash: string,
    file: File,
    chapterIndices: number[],
    documentType?: string,
    description?: string
  ): Promise<IngestTaskOut>
  getConfig(): Promise<ConfigOut>
  getTaskStatus(taskId: string): Promise<TaskStatusOut>
  listActiveTasks(): Promise<ActiveTasksOut>
  summarizeChapter(chapter: number, chapterIndex: number, bookTitle: string, documentHash: string, force?: boolean): Promise<TaskResponseOut>
  generateFlashcards(chapter: number, chapterIndex: number, bookTitle: string, documentHash: string, force?: boolean): Promise<TaskResponseOut>
  getStoredSummary(docHash: string, chapter: number, chapterIndex?: number): Promise<SummaryResponse | null>
  deleteSummary(docHash: string, chapter: number, chapterIndex?: number): Promise<void>
  getStoredFlashcards(docHash: string, chapter: number, chapterIndex?: number): Promise<FlashcardResponse[]>
  getPendingFlashcards(docHash: string, chapter?: number, chapterIndex?: number): Promise<FlashcardResponse[]>
  approveFlashcards(docHash: string, flashcardIds: string[]): Promise<void>
  rejectFlashcards(docHash: string, flashcardIds: string[]): Promise<void>
  approveAllFlashcards(docHash: string, chapter?: number, chapterIndex?: number): Promise<void>
  getMetadata(docHash: string): Promise<MetadataResponse>
  saveMetadata(docHash: string, description: string, documentType?: string): Promise<MetadataResponse>
  submitExamResult(docHash: string, chapter: number, totalCards: number, correctCount: number): Promise<ExamResultOut>
  getExamStatus(docHash: string): Promise<ChapterExamStatusOut[]>
  getExamStatusForChapter(docHash: string, chapter: number): Promise<ChapterExamStatusOut>
  chat(
    docHash: string,
    query: string,
    chapter: number | null,
    chapterIndex: number | null,
    history: Array<{ role: 'user' | 'assistant'; content: string }>
  ): Promise<ChatResponse>
  getDocumentFileUrl(docHash: string): string
  getChapterPdfUrl(docHash: string, chapter: number): string
  createDocument(req: CreateDocumentRequest): Promise<CreateDocumentResponse>
  appendContent(docHash: string, content: string): Promise<AppendContentResponse>
  getDocumentContent(docHash: string): Promise<DocumentContentResponse>
  updateDocumentContent(docHash: string, content: string): Promise<UpdateContentResponse>
}

export type { ServiceClient as ServiceClientType }
