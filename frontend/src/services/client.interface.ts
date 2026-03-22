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

export interface ServiceClient {
  health(): Promise<HealthOut>
  listDocuments(): Promise<DocumentOut[]>
  documentStructure(hash: string): Promise<DocumentStructureOut>
  deleteDocument(hash: string): Promise<void>
  ingestDocument(formData: FormData): Promise<IngestTaskOut>
  getConfig(): Promise<ConfigOut>
  getTaskStatus(taskId: string): Promise<TaskStatusOut>
  summarizeChapter(chapter: number, bookTitle: string, documentHash: string): Promise<TaskResponseOut>
  generateFlashcards(chapter: number, bookTitle: string, documentHash: string): Promise<TaskResponseOut>
  getStoredSummary(docHash: string, chapter: number): Promise<SummaryResponse | null>
  getStoredFlashcards(docHash: string, chapter: number): Promise<FlashcardResponse[]>
  getMetadata(docHash: string): Promise<MetadataResponse>
  saveMetadata(docHash: string, description: string, documentType?: string): Promise<MetadataResponse>
}

export type { ServiceClient as ServiceClientType }
