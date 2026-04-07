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
  CreateDocumentRequest,
  CreateDocumentResponse,
  AppendContentResponse,
  DocumentContentResponse,
  UpdateContentResponse,
} from '../types/api'
import type { KnowledgeTree, KnowledgeChapter, KnowledgeDocument } from '../types/knowledge-tree'

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
  getDocumentFileUrl(docHash: string): string
  getChapterPdfUrl(docHash: string, chapter: number): string
  createDocument(req: CreateDocumentRequest): Promise<CreateDocumentResponse>
  appendContent(docHash: string, content: string): Promise<AppendContentResponse>
  getDocumentContent(docHash: string): Promise<DocumentContentResponse>
  updateDocumentContent(docHash: string, content: string): Promise<UpdateContentResponse>

  // Knowledge Trees
  listKnowledgeTrees(): Promise<KnowledgeTree[]>
  createKnowledgeTree(title: string, description?: string): Promise<KnowledgeTree>
  updateKnowledgeTree(id: string, title: string, description?: string): Promise<KnowledgeTree>
  deleteKnowledgeTree(id: string): Promise<void>
  getKnowledgeTreeChapters(treeId: string): Promise<KnowledgeChapter[]>
  createKnowledgeChapter(treeId: string, title: string): Promise<KnowledgeChapter>
  updateKnowledgeChapter(treeId: string, chapterNumber: number, title: string): Promise<KnowledgeChapter>
  deleteKnowledgeChapter(treeId: string, chapterNumber: number): Promise<void>
  listKnowledgeDocuments(treeId: string, chapterId?: string | null): Promise<KnowledgeDocument[]>
  createKnowledgeDocument(treeId: string, chapter: number | null, title: string, content: string, isMain?: boolean): Promise<KnowledgeDocument>
  updateKnowledgeDocument(id: string, title: string, content: string): Promise<KnowledgeDocument>
  deleteKnowledgeDocument(id: string): Promise<void>
  ingestFileAsKnowledgeDocument(treeId: string, chapter: number, file: File): Promise<KnowledgeDocument>
  previewKnowledgeTreeFile(file: File): Promise<DocumentPreviewOut>
  createKnowledgeTreeFromFile(file: File, title?: string, chapterIndices?: number[]): Promise<{ task_id: string }>
}

export type { ServiceClient as ServiceClientType }
