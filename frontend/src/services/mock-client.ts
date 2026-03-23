import { mockHealth } from '../mocks/health'
import { mockDocuments, mockDocumentStructures } from '../mocks/documents'
import { mockConfig } from '../mocks/config'
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
} from '../types/api'
import type { ServiceClient } from './client.interface'

const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

export class MockClient implements ServiceClient {
  private deletedHashes = new Set<string>()
  private taskCallCounts = new Map<string, number>()
  private metadataStore = new Map<string, { description: string; document_type: string }>()

  async health(): Promise<HealthOut> {
    await delay(100)
    return { ...mockHealth }
  }

  async listDocuments(): Promise<DocumentOut[]> {
    await delay(200)
    return mockDocuments.filter((doc) => !this.deletedHashes.has(doc.file_hash))
  }

  async documentStructure(hash: string): Promise<DocumentStructureOut> {
    await delay(200)
    const structure = mockDocumentStructures[hash]
    if (!structure) {
      throw new Error(`Document not found: ${hash}`)
    }
    return { ...structure }
  }

  async deleteDocument(hash: string): Promise<void> {
    await delay(100)
    this.deletedHashes.add(hash)
  }

  async deleteChapter(_docHash: string, chapterNumber: number): Promise<ChapterDeleteResponse> {
    await delay(150)
    return {
      message: `Removed chapter ${chapterNumber}`,
      vectors_deleted: 42,
      summaries_deleted: 1,
      flashcards_deleted: 10,
    }
  }

  async ingestDocument(formData: FormData): Promise<IngestTaskOut> {
    await delay(300)
    const taskId = `mock-task-${Math.random().toString(36).slice(2, 10)}`
    const filename = (formData.get('file') as File | null)?.name ?? 'unknown.pdf'
    return { task_id: taskId, filename }
  }

  async getConfig(): Promise<ConfigOut> {
    await delay(150)
    return { ...mockConfig }
  }

  async getTaskStatus(taskId: string): Promise<TaskStatusOut> {
    await delay(150)
    const count = this.taskCallCounts.get(taskId) ?? 0
    this.taskCallCounts.set(taskId, count + 1)

    if (count === 0) {
      return { task_id: taskId, status: 'pending', progress: 'Queued...' }
    } else if (count === 1) {
      return { task_id: taskId, status: 'running', progress: 'Chunking document...' }
    } else if (count === 2) {
      return { task_id: taskId, status: 'running', progress: 'Generating embeddings...' }
    } else {
      return {
        task_id: taskId,
        status: 'completed',
        progress: 'Done',
        result: { message: 'Done' },
      }
    }
  }

  async summarizeChapter(_chapter: number, _bookTitle: string, _documentHash: string): Promise<TaskResponseOut> {
    await delay(200)
    return {
      task_id: `sum-task-${Math.random().toString(36).slice(2, 10)}`,
      task_type: 'summarize',
    }
  }

  async generateFlashcards(_chapter: number, _bookTitle: string, _documentHash: string): Promise<TaskResponseOut> {
    await delay(200)
    return {
      task_id: `fc-task-${Math.random().toString(36).slice(2, 10)}`,
      task_type: 'generate_flashcards',
    }
  }

  async getStoredSummary(_docHash: string, _chapter: number): Promise<SummaryResponse | null> {
    await delay(100)
    return null
  }

  async getStoredFlashcards(_docHash: string, _chapter: number): Promise<FlashcardResponse[]> {
    await delay(100)
    return []
  }

  async getMetadata(docHash: string): Promise<MetadataResponse> {
    await delay(100)
    const stored = this.metadataStore.get(docHash)
    return {
      document_hash: docHash,
      description: stored?.description ?? '',
      document_type: stored?.document_type ?? '',
    }
  }

  async saveMetadata(docHash: string, description: string, documentType = ''): Promise<MetadataResponse> {
    await delay(100)
    this.metadataStore.set(docHash, { description, document_type: documentType })
    return { document_hash: docHash, description, document_type: documentType }
  }
}
