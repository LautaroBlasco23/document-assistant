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
  ActiveTasksOut,
  DocumentPreviewOut,
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

  async previewDocument(_file: File): Promise<DocumentPreviewOut> {
    await delay(500)
    return {
      file_hash: 'mock-preview-hash',
      filename: 'mock-document.pdf',
      num_chapters: 5,
      chapters: [
        { index: 0, title: 'Introduction', page_start: 1, page_end: 10 },
        { index: 1, title: 'Chapter 1: Getting Started', page_start: 11, page_end: 25 },
        { index: 2, title: 'Chapter 2: Core Concepts', page_start: 26, page_end: 50 },
        { index: 3, title: 'Chapter 3: Advanced Topics', page_start: 51, page_end: 80 },
        { index: 4, title: 'Conclusion', page_start: 81, page_end: 90 },
      ],
    }
  }

  async ingestDocumentChapters(
    _fileHash: string,
    _file: File,
    _chapterIndices: number[],
    _documentType?: string,
    _description?: string
  ): Promise<IngestTaskOut> {
    await delay(300)
    const taskId = `mock-task-${Math.random().toString(36).slice(2, 10)}`
    return { task_id: taskId, filename: 'mock-document.pdf' }
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

  async listActiveTasks(): Promise<ActiveTasksOut> {
    await delay(100)
    return { tasks: [] }
  }

  async summarizeChapter(_chapter: number, _qdrantIndex: number, _bookTitle: string, _documentHash: string, _force?: boolean): Promise<TaskResponseOut> {
    await delay(200)
    return {
      task_id: `sum-task-${Math.random().toString(36).slice(2, 10)}`,
      task_type: 'summarize',
    }
  }

  async generateFlashcards(_chapter: number, _qdrantIndex: number, _bookTitle: string, _documentHash: string, _force?: boolean): Promise<TaskResponseOut> {
    await delay(200)
    return {
      task_id: `fc-task-${Math.random().toString(36).slice(2, 10)}`,
      task_type: 'generate_flashcards',
    }
  }

  async getStoredSummary(_docHash: string, _chapter: number, _qdrantIndex?: number): Promise<SummaryResponse | null> {
    await delay(100)
    return null
  }

  async deleteSummary(_docHash: string, _chapter: number, _qdrantIndex?: number): Promise<void> {
    await delay(100)
  }

  async getStoredFlashcards(_docHash: string, _chapter: number, _qdrantIndex?: number): Promise<FlashcardResponse[]> {
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
