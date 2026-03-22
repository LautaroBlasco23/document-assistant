import { mockHealth } from '../mocks/health'
import { mockDocuments, mockDocumentStructures } from '../mocks/documents'
import { mockChunks } from '../mocks/chunks'
import { mockConfig } from '../mocks/config'
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
import type { ServiceClient } from './client.interface'

const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

const CANNED_ANSWERS: Record<string, string> = {
  a1b2c3d4e5f6:
    'Machine learning is a fascinating field that enables computers to learn from data without being explicitly programmed. ' +
    'The key insight is that instead of writing rules manually, we let the algorithm discover patterns in training data. ' +
    'Supervised learning works by mapping inputs to outputs using labeled examples, while unsupervised learning finds hidden structure in unlabeled data. ' +
    'Neural networks, inspired by the brain, are particularly powerful because they can learn complex non-linear representations. ' +
    'In practice, feature engineering — transforming raw data into meaningful inputs — often matters more than the choice of algorithm itself.',

  d4e5f67890ab:
    'Clean Architecture is about separating concerns so that each layer of the system has a clear, single responsibility. ' +
    'The dependency rule is the central principle: source code dependencies must always point inward toward higher-level policy. ' +
    'Business rules and use cases sit at the core, completely isolated from frameworks, databases, and delivery mechanisms. ' +
    'This separation means you can test your business logic without standing up a web server or connecting to a database. ' +
    'The practical benefit is that you can swap out any infrastructure component — the database, the web framework — without touching your core logic.',

  g7h8i9j0k1l2:
    'Sun Tzu teaches that strategy is fundamentally about shaping conditions before conflict begins. ' +
    'The supreme victory is achieved without fighting at all — by making your position so strong that the enemy concedes. ' +
    'Deception is central: appear weak when strong, inactive when ready to strike, far when near. ' +
    'Knowing both yourself and your enemy removes the element of chance from battle. ' +
    'Opportunities compound when seized; the winning general calculates extensively before the battle, while the losing general calculates too little.',
}

const DEFAULT_ANSWER =
  'This is a helpful answer based on the document contents. ' +
  'The text covers several important concepts that build on each other progressively. ' +
  'Key ideas emerge from a careful reading of the chapter structure and supporting evidence. ' +
  'Further exploration of the later chapters will deepen your understanding of these foundational concepts.'

export class MockClient implements ServiceClient {
  private deletedHashes = new Set<string>()
  private taskCallCounts = new Map<string, number>()

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

  async ingestDocument(formData: FormData): Promise<IngestTaskOut> {
    await delay(300)
    const taskId = `mock-task-${Math.random().toString(36).slice(2, 10)}`
    const filename = (formData.get('file') as File | null)?.name ?? 'unknown.pdf'
    return { task_id: taskId, filename }
  }

  async search(query: string, k: number = 5, chapter?: number, _book?: string): Promise<SearchResultsOut> {
    await delay(200)
    const lower = query.toLowerCase()
    let results = mockChunks.filter((chunk) => chunk.text.toLowerCase().includes(lower))

    if (chapter !== undefined) {
      results = results.filter((chunk) => chunk.chapter === chapter)
    }

    // Sort by score descending and take top-k
    const topK = results
      .slice()
      .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
      .slice(0, k)

    return {
      query,
      chunks: topK,
      count: topK.length,
    }
  }

  async streamAsk(
    query: string,
    _chapter: number | undefined,
    onEvent: (event: SSEEvent) => void
  ): Promise<void> {
    // Pick a canned answer based on which document hash appears in the query context.
    // Since streamAsk doesn't receive a hash directly, we try to match a known answer
    // by looking for hash substrings in the query; otherwise use the generic answer.
    let answer = DEFAULT_ANSWER
    for (const [hash, text] of Object.entries(CANNED_ANSWERS)) {
      if (query.toLowerCase().includes(hash.toLowerCase())) {
        answer = text
        break
      }
    }

    const words = answer.split(' ')
    for (const word of words) {
      await delay(60)
      onEvent({ type: 'token', data: { token: word + ' ' } })
    }

    onEvent({
      type: 'done',
      data: { sources: mockChunks.slice(0, 3) },
    })
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

  async generateQA(_chapter: number, _bookTitle: string, _documentHash: string): Promise<TaskResponseOut> {
    await delay(200)
    return {
      task_id: `qa-task-${Math.random().toString(36).slice(2, 10)}`,
      task_type: 'generate_qa',
    }
  }

  async generateFlashcards(_chapter: number, _bookTitle: string, _documentHash: string): Promise<TaskResponseOut> {
    await delay(200)
    return {
      task_id: `fc-task-${Math.random().toString(36).slice(2, 10)}`,
      task_type: 'generate_flashcards',
    }
  }
}
