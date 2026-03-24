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
  summarizeChapter(chapter: number, qdrantIndex: number, bookTitle: string, documentHash: string, force?: boolean): Promise<TaskResponseOut>
  generateFlashcards(chapter: number, qdrantIndex: number, bookTitle: string, documentHash: string, force?: boolean): Promise<TaskResponseOut>
  getStoredSummary(docHash: string, chapter: number, qdrantIndex?: number): Promise<SummaryResponse | null>
  deleteSummary(docHash: string, chapter: number, qdrantIndex?: number): Promise<void>
  getStoredFlashcards(docHash: string, chapter: number, qdrantIndex?: number): Promise<FlashcardResponse[]>
  getMetadata(docHash: string): Promise<MetadataResponse>
  saveMetadata(docHash: string, description: string, documentType?: string): Promise<MetadataResponse>
}

export type { ServiceClient as ServiceClientType }
