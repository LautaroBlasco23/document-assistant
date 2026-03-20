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

export interface ServiceClient {
  health(): Promise<HealthOut>
  listDocuments(): Promise<DocumentOut[]>
  documentStructure(hash: string): Promise<DocumentStructureOut>
  deleteDocument(hash: string): Promise<void>
  ingestDocument(formData: FormData): Promise<IngestTaskOut>
  search(query: string, k?: number, chapter?: number, book?: string): Promise<SearchResultsOut>
  streamAsk(
    query: string,
    chapter: number | undefined,
    onEvent: (event: SSEEvent) => void
  ): Promise<void>
  getConfig(): Promise<ConfigOut>
  getTaskStatus(taskId: string): Promise<TaskStatusOut>
  summarizeChapter(chapter: number, bookTitle: string): Promise<TaskResponseOut>
  generateQA(chapter: number, bookTitle: string): Promise<TaskResponseOut>
  generateFlashcards(chapter: number, bookTitle: string): Promise<TaskResponseOut>
}

export type { ServiceClient as ServiceClientType }
