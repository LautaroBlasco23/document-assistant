import { mockHealth } from '../mocks/health'
import { mockConfig } from '../mocks/config'
import { mockKnowledgeTrees, mockKnowledgeChapters, mockKnowledgeDocuments } from '../mocks/knowledge-trees'
import { mockExamQuestions } from '../mocks/knowledge-exam'
import type { KnowledgeTree, KnowledgeChapter, KnowledgeDocument, ExamSession, CreateExamSessionPayload, StudySession, CreateStudySessionPayload } from '../types/knowledge-tree'
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
  ProviderInfo,
  CredentialStatus,
  TestConnectionResult,
  AuthTokenResponse,
  UserProfile,
} from '../types/api'
import type { ServiceClient } from './client.interface'

const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

export class MockClient implements ServiceClient {
  private taskCallCounts = new Map<string, number>()

  // Knowledge Tree in-memory state
  private trees: KnowledgeTree[] = [...mockKnowledgeTrees]
  private chapters: Map<string, KnowledgeChapter[]> = new Map(
    Object.entries(mockKnowledgeChapters).map(([k, v]) => [k, [...v]])
  )
  private documents: KnowledgeDocument[] = [...mockKnowledgeDocuments]
  private deletedTreeIds = new Set<string>()

  // Agents in-memory state
  private agents: AgentOut[] = [
    {
      id: 'agent-default',
      name: 'Default',
      provider: '',
      prompt: '',
      model: 'mock-model',
      temperature: 0.7,
      top_p: 1.0,
      max_tokens: 1024,
      is_default: true,
      created_at: new Date().toISOString(),
    },
  ]
  private agentCounter = 1

  async health(): Promise<HealthOut> {
    await delay(100)
    return { ...mockHealth }
  }

  async getConfig(): Promise<ConfigOut> {
    await delay(150)
    return { ...mockConfig }
  }

  async getModels(_provider?: string): Promise<ModelsOut> {
    await delay(100)
    return { provider: _provider ?? 'mock', current_model: 'mock-model', models: [] }
  }

  // Agents
  async listAgents(): Promise<AgentOut[]> {
    await delay(100)
    return [...this.agents]
  }

  async createAgent(req: CreateAgentRequest): Promise<AgentOut> {
    await delay(150)
    this.agentCounter++
    const agent: AgentOut = {
      id: `agent-${this.agentCounter}`,
      name: req.name,
      provider: req.provider,
      prompt: req.prompt ?? '',
      model: req.model,
      temperature: req.temperature ?? 0.7,
      top_p: req.top_p ?? 1.0,
      max_tokens: req.max_tokens ?? 1024,
      is_default: false,
      created_at: new Date().toISOString(),
    }
    this.agents.push(agent)
    return agent
  }

  async updateAgent(id: string, req: UpdateAgentRequest): Promise<AgentOut> {
    await delay(150)
    const idx = this.agents.findIndex((a) => a.id === id)
    if (idx === -1) throw new Error('Agent not found')
    const agent = this.agents[idx]
    const updated: AgentOut = {
      ...agent,
      name: req.name ?? agent.name,
      provider: req.provider ?? agent.provider,
      model: req.model ?? agent.model,
      temperature: req.temperature ?? agent.temperature,
      top_p: req.top_p ?? agent.top_p,
      max_tokens: req.max_tokens ?? agent.max_tokens,
    }
    if (req.is_default === true) {
      this.agents = this.agents.map((a) => ({ ...a, is_default: a.id === id }))
      updated.is_default = true
    } else if (req.is_default === false) {
      updated.is_default = false
    }
    this.agents[idx] = updated
    return updated
  }

  async deleteAgent(id: string): Promise<void> {
    await delay(100)
    this.agents = this.agents.filter((a) => a.id !== id)
  }

  async getDefaultAgent(): Promise<AgentOut> {
    await delay(100)
    const def = this.agents.find((a) => a.is_default)
    if (def) return def
    return this.agents[0]
  }

  async setDefaultAgent(agentId: string): Promise<AgentOut> {
    return this.updateAgent(agentId, { is_default: true })
  }

  async getTaskStatus(taskId: string): Promise<TaskStatusOut> {
    await delay(150)
    const count = this.taskCallCounts.get(taskId) ?? 0
    this.taskCallCounts.set(taskId, count + 1)

    if (count === 0) {
      return { task_id: taskId, status: 'pending', progress: 'Queued...' }
    } else if (count === 1) {
      return { task_id: taskId, status: 'running', progress: 'Processing...' }
    } else if (count === 2) {
      return { task_id: taskId, status: 'running', progress: 'Storing results...' }
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

  // Knowledge Trees

  async listKnowledgeTrees(): Promise<KnowledgeTree[]> {
    await delay(150)
    return this.trees.filter((t) => !this.deletedTreeIds.has(t.id))
  }

  async createKnowledgeTree(title: string, description?: string): Promise<KnowledgeTree> {
    await delay(200)
    const id = `tree-${Math.random().toString(36).slice(2, 10)}`
    const tree: KnowledgeTree = {
      id,
      title,
      description,
      num_chapters: 0,
      created_at: new Date().toISOString(),
    }
    this.trees.push(tree)
    this.chapters.set(id, [])
    const mainDoc: KnowledgeDocument = {
      id: `doc-${id}-main`,
      tree_id: id,
      chapter_id: null,
      chapter_number: null,
      is_main: true,
      title: 'Overview',
      content: '',
      original_content: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    this.documents.push(mainDoc)
    return tree
  }

  async updateKnowledgeTree(id: string, title: string, description?: string): Promise<KnowledgeTree> {
    await delay(150)
    const tree = this.trees.find((t) => t.id === id)
    if (!tree) throw new Error(`Tree not found: ${id}`)
    tree.title = title
    tree.description = description
    return { ...tree }
  }

  async deleteKnowledgeTree(id: string): Promise<void> {
    await delay(150)
    this.deletedTreeIds.add(id)
  }

  async getKnowledgeTreeChapters(treeId: string): Promise<KnowledgeChapter[]> {
    await delay(100)
    return this.chapters.get(treeId) ?? []
  }

  async createKnowledgeChapter(treeId: string, title: string): Promise<KnowledgeChapter> {
    await delay(150)
    const existing = this.chapters.get(treeId) ?? []
    const number = existing.length + 1
    const chapter: KnowledgeChapter = { id: crypto.randomUUID(), number, title, status: 'pending', tree_id: treeId }
    this.chapters.set(treeId, [...existing, chapter])
    const tree = this.trees.find((t) => t.id === treeId)
    if (tree) tree.num_chapters = number
    return chapter
  }

  async updateKnowledgeChapter(treeId: string, chapterNumber: number, title: string): Promise<KnowledgeChapter> {
    await delay(150)
    const chapters = this.chapters.get(treeId) ?? []
    const chapter = chapters.find((c) => c.number === chapterNumber)
    if (!chapter) throw new Error(`Chapter not found: ${chapterNumber}`)
    chapter.title = title
    return { ...chapter }
  }

  async markKnowledgeChapterRead(treeId: string, chapterNumber: number): Promise<void> {
    await delay(100)
    const existing = this.chapters.get(treeId) ?? []
    const chapter = existing.find((c) => c.number === chapterNumber)
    if (chapter) chapter.status = 'read'
  }

  async deleteKnowledgeChapter(treeId: string, chapterNumber: number): Promise<void> {
    await delay(150)
    const existing = this.chapters.get(treeId) ?? []
    this.chapters.set(treeId, existing.filter((c) => c.number !== chapterNumber))
    this.documents = this.documents.filter(
      (d) => !(d.tree_id === treeId && d.chapter_number === chapterNumber)
    )
    const tree = this.trees.find((t) => t.id === treeId)
    if (tree) tree.num_chapters = Math.max(0, tree.num_chapters - 1)
  }

  async deleteKnowledgeChapters(treeId: string, chapterNumbers: number[]): Promise<void> {
    await delay(150)
    const existing = this.chapters.get(treeId) ?? []
    const deletedSet = new Set(chapterNumbers)
    this.chapters.set(treeId, existing.filter((c) => !deletedSet.has(c.number)))
    this.documents = this.documents.filter(
      (d) => !(d.tree_id === treeId && d.chapter_number !== null && deletedSet.has(d.chapter_number))
    )
    const tree = this.trees.find((t) => t.id === treeId)
    if (tree) tree.num_chapters = Math.max(0, tree.num_chapters - chapterNumbers.length)
  }

  async listKnowledgeDocuments(treeId: string, chapterId?: string | null): Promise<KnowledgeDocument[]> {
    await delay(100)
    if (chapterId === undefined || chapterId === null) {
      return this.documents.filter((d) => d.tree_id === treeId)
    }
    const treeChapters = this.chapters.get(treeId) ?? []
    const chapter = treeChapters.find((c) => c.id === chapterId)
    if (!chapter) return []
    return this.documents.filter((d) => d.tree_id === treeId && d.chapter_number === chapter.number)
  }

  async createKnowledgeDocument(
    treeId: string,
    chapterId: string | null,
    title: string,
    content: string,
    isMain = false,
  ): Promise<KnowledgeDocument> {
    await delay(150)
    const chapterNum = chapterId !== null
      ? (this.chapters.get(treeId) ?? []).find((c) => c.id === chapterId)?.number ?? null
      : null
    const doc: KnowledgeDocument = {
      id: `doc-${Math.random().toString(36).slice(2, 12)}`,
      tree_id: treeId,
      chapter_id: chapterId,
      chapter_number: chapterNum,
      is_main: isMain,
      title,
      content,
      original_content: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    this.documents.push(doc)
    return doc
  }

  async updateKnowledgeDocument(_treeId: string, id: string, title: string, content: string, fileType?: string | null, originalContent?: string | null): Promise<KnowledgeDocument> {
    await delay(150)
    const idx = this.documents.findIndex((d) => d.id === id)
    if (idx === -1) throw new Error(`Document not found: ${id}`)
    const updated = {
      ...this.documents[idx],
      title,
      content,
      file_type: fileType !== undefined ? fileType ?? undefined : this.documents[idx].file_type,
      original_content:
        originalContent !== undefined
          ? (this.documents[idx].original_content ?? originalContent ?? null)
          : this.documents[idx].original_content,
      updated_at: new Date().toISOString(),
    }
    this.documents[idx] = updated
    return updated
  }

  async deleteKnowledgeDocument(_treeId: string, id: string): Promise<void> {
    await delay(100)
    this.documents = this.documents.filter((d) => d.id !== id)
  }

  async improveKnowledgeDocument(_treeId: string, _docId: string, _agentId?: string, _mode: 'text' | 'formatting' = 'text'): Promise<{ task_id: string }> {
    await delay(1200)
    return { task_id: `mock-improve-${_docId}` }
  }

  async revertKnowledgeDocument(_treeId: string, docId: string): Promise<KnowledgeDocument> {
    await delay(300)
    const doc = this.documents.find((d) => d.id === docId)
    if (!doc || !doc.original_content) throw new Error('Document not found or has no improvement to revert')
    const updated = { ...doc, content: doc.original_content, original_content: null }
    this.documents = this.documents.map((d) => d.id === docId ? updated : d)
    return updated
  }

  async splitKnowledgeChapter(
    treeId: string,
    chapterNumber: number,
    entries: { page_start: number; page_end: number; title?: string | null }[]
  ): Promise<{ chapters: KnowledgeChapter[] }> {
    await delay(200)
    const existing = this.chapters.get(treeId) ?? []
    const chapter = existing.find((c) => c.number === chapterNumber)
    if (!chapter) throw new Error(`Chapter not found: ${chapterNumber}`)

    const pdfDoc = this.documents.find(
      (d) => d.tree_id === treeId && d.chapter_number === chapterNumber && d.source_file_path && d.page_start != null && d.page_end != null
    )
    if (!pdfDoc) throw new Error('No PDF document with page range found for this chapter')

    const maxOffset = pdfDoc.page_end! - pdfDoc.page_start!

    if (entries.length < 2) throw new Error('Must split into at least 2 chapters')
    for (let i = 0; i < entries.length; i++) {
      const e = entries[i]
      if (e.page_start > e.page_end) throw new Error(`Entry ${i + 1}: page_start must be ≤ page_end`)
      if (e.page_start < 0 || e.page_end > maxOffset) throw new Error(`Entry ${i + 1}: range exceeds chapter range (0-${maxOffset})`)
      if (i > 0 && e.page_start !== entries[i - 1].page_end + 1) throw new Error(`Entry ${i + 1}: chapters must be contiguous`)
    }
    if (entries[entries.length - 1].page_end !== maxOffset) throw new Error('Last chapter must end at the last page')

    const numNewChapters = entries.length - 1
    const absBase = pdfDoc.page_start!

    const updatedChapters = existing.map((c) =>
      c.number > chapterNumber ? { ...c, number: c.number + numNewChapters } : c
    )

    const newChapters: KnowledgeChapter[] = []
    for (let i = 1; i < entries.length; i++) {
      const newNumber = chapterNumber + i
      const entry = entries[i]
      const newChapter: KnowledgeChapter = {
        id: crypto.randomUUID(),
        number: newNumber,
        title: entry.title ?? `Chapter ${newNumber}`,
        status: 'pending',
        tree_id: treeId,
      }
      newChapters.push(newChapter)

      const newDoc: KnowledgeDocument = {
        ...pdfDoc,
        id: `doc-${crypto.randomUUID().slice(0, 8)}`,
        chapter_id: newChapter.id,
        chapter_number: newNumber,
        page_start: absBase + entry.page_start,
        page_end: absBase + entry.page_end,
        title: entry.title ?? `${pdfDoc.title} (Part ${i + 1})`,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }
      this.documents.push(newDoc)
    }

    pdfDoc.page_start = absBase + entries[0].page_start
    pdfDoc.page_end = absBase + entries[0].page_end

    const insertAt = updatedChapters.findIndex((c) => c.number > chapterNumber)
    const spliceIdx = insertAt === -1 ? updatedChapters.length : insertAt
    updatedChapters.splice(spliceIdx, 0, ...newChapters)
    this.chapters.set(treeId, updatedChapters)

    const tree = this.trees.find((t) => t.id === treeId)
    if (tree) tree.num_chapters = updatedChapters.length

    const resultChapters = updatedChapters.filter(
      (c) => c.number >= chapterNumber && c.number < chapterNumber + entries.length
    )
    return { chapters: resultChapters }
  }

  async ingestFileAsKnowledgeDocument(treeId: string, chapter: number, file: File): Promise<{ task_id: string }> {
    await delay(1500)
    const extractedContent = `[Extracted from ${file.name}]\n\nSimulated text content from ${file.type || 'file'}.\n\nFile size: ${(file.size / 1024).toFixed(1)} KB`
    const title = file.name.replace(/\.(pdf|epub)$/i, '')
    const chapterId = (this.chapters.get(treeId) ?? []).find((c) => c.number === chapter)?.id ?? null
    await this.createKnowledgeDocument(treeId, chapterId, title, extractedContent)
    return { task_id: `mock-task-${Math.random().toString(36).slice(2, 10)}` }
  }

  async importYouTubeDocument(treeId: string, url: string, chapterId?: string | null): Promise<{ task_id: string }> {
    await delay(2000)
    const videoId = url.match(/(?:v=|youtu\.be\/)([A-Za-z0-9_-]{11})/)?.[1] ?? 'unknown'
    const title = `YouTube: ${videoId}`
    const content = `[00:00] Simulated transcript for video ${videoId} from ${url}\n\n[00:30] This is mock content for development.`
    await this.createKnowledgeDocument(treeId, chapterId ?? null, title, content)
    return { task_id: `mock-task-${Math.random().toString(36).slice(2, 10)}` }
  }

  async previewKnowledgeTreeFile(file: File): Promise<DocumentPreviewOut> {
    await delay(600)
    return {
      file_hash: `mock-hash-${Math.random().toString(36).slice(2, 18)}`,
      filename: file.name,
      num_chapters: 4,
      chapters: [
        { index: 0, title: 'Introduction', page_start: 1, page_end: 15 },
        { index: 1, title: 'Chapter 1: Foundations', page_start: 16, page_end: 45 },
        { index: 2, title: 'Chapter 2: Advanced Topics', page_start: 46, page_end: 90 },
        { index: 3, title: 'Conclusion', page_start: 91, page_end: 100 },
      ],
    }
  }

  async createKnowledgeTreeFromFile(file: File, title?: string, chapterIndices?: number[]): Promise<{ task_id: string }> {
    console.log('[MockClient] createKnowledgeTreeFromFile', file.name, title, chapterIndices)
    await delay(200)
    const taskId = `mock-task-${Math.random().toString(36).slice(2, 10)}`
    return { task_id: taskId }
  }

  async exportKnowledgeTree(_treeId: string): Promise<Blob> {
    await delay(500)
    return new Blob(['PK stub zip'], { type: 'application/zip' })
  }

  // Document Reader
  getDocumentFileUrl(_treeId: string, docId: string): string {
    return `#mock-file-${docId}`
  }

  getDocumentThumbnailUrl(_treeId: string, _docId: string): string {
    return ''
  }

  async generateFlashcardFromSelection(_treeId: string, _chapter: number, _selectedText: string): Promise<{ task_id: string }> {
    await delay(500)
    return { task_id: `mock-task-${Math.random().toString(36).slice(2, 10)}` }
  }

  async draftFlashcard(_treeId: string, _chapter: number, selectedText: string, _model?: string, _agentId?: string) {
    await delay(400)
    return {
      front: `What is described by: "${selectedText.slice(0, 60)}..."?`,
      back: `Mock answer derived from: ${selectedText.slice(0, 120)}`,
      source_text: selectedText,
    }
  }

  async saveFlashcard(_treeId: string, _chapter: number, _payload: { front: string; back: string; source_text?: string | null }) {
    await delay(150)
    return { id: `mock-fc-${Math.random().toString(36).slice(2, 10)}` }
  }

  async draftQuestion(
    _treeId: string,
    _chapter: number,
    questionType: KnowledgeTreeQuestionType,
    selectedText: string,
    _model?: string,
    _agentId?: string,
  ) {
    await delay(400)
    if (questionType === 'true_false') {
      return {
        question_type: questionType,
        question_data: {
          statement: `According to the text, ${selectedText.slice(0, 80)}.`,
          answer: true,
          explanation: 'Mock explanation.',
        } as Record<string, unknown>,
      }
    }
    return {
      question_type: questionType,
      question_data: {
        question: `What does the excerpt "${selectedText.slice(0, 50)}..." imply?`,
        choices: ['Option A', 'Option B', 'Option C', 'Option D'],
        correct_index: 0,
        explanation: 'Mock explanation.',
      } as Record<string, unknown>,
    }
  }

  async saveQuestion(
    _treeId: string,
    _chapter: number,
    _questionType: KnowledgeTreeQuestionType,
    _questionData: Record<string, unknown>,
  ) {
    await delay(150)
    return { id: `mock-q-${Math.random().toString(36).slice(2, 10)}` }
  }

  // Knowledge Tree Questions

  async generateKnowledgeTreeQuestions(
    _treeId: string,
    _chapter: number,
    _questionTypes?: KnowledgeTreeQuestionType[],
    _model?: string,
    _agentId?: string,
    _numQuestions?: number | null,
  ): Promise<{ task_id: string }> {
    await delay(150)
    return { task_id: 'mock-task-id' }
  }

  async getKnowledgeTreeQuestions(
    _treeId: string,
    _chapter: number,
    type?: KnowledgeTreeQuestionType
  ): Promise<KnowledgeTreeQuestionOut[]> {
    await delay(100)
    const typeMap: Record<KnowledgeTreeQuestionType, KnowledgeTreeQuestionOut[]> = {
      true_false: mockExamQuestions
        .filter((q) => q.type === 'true-false')
        .map((q) => {
          const tf = q as { type: string; id: string; statement: string; answer: boolean; explanation?: string }
          return {
            id: tf.id,
            question_type: 'true_false' as KnowledgeTreeQuestionType,
            question_data: {
              statement: tf.statement,
              answer: tf.answer,
              explanation: tf.explanation,
            },
            created_at: new Date().toISOString(),
          }
        }),
      multiple_choice: mockExamQuestions
        .filter((q) => q.type === 'multiple-choice')
        .map((q) => {
          const mc = q as { type: string; id: string; question: string; choices: string[]; correctIndex: number; explanation?: string }
          return {
            id: mc.id,
            question_type: 'multiple_choice' as KnowledgeTreeQuestionType,
            question_data: {
              question: mc.question,
              choices: mc.choices,
              correct_index: mc.correctIndex,
              explanation: mc.explanation,
            },
            created_at: new Date().toISOString(),
          }
        }),
      matching: mockExamQuestions
        .filter((q) => q.type === 'matching')
        .map((q) => {
          const m = q as { type: string; id: string; prompt: string; pairs: Array<{ term: string; definition: string }> }
          return {
            id: m.id,
            question_type: 'matching' as KnowledgeTreeQuestionType,
            question_data: {
              prompt: m.prompt,
              pairs: m.pairs,
            },
            created_at: new Date().toISOString(),
          }
        }),
      checkbox: mockExamQuestions
        .filter((q) => q.type === 'checkbox')
        .map((q) => {
          const cb = q as { type: string; id: string; question: string; choices: string[]; correctIndices: number[]; explanation?: string }
          return {
            id: cb.id,
            question_type: 'checkbox' as KnowledgeTreeQuestionType,
            question_data: {
              question: cb.question,
              choices: cb.choices,
              correct_indices: cb.correctIndices,
              explanation: cb.explanation,
            },
            created_at: new Date().toISOString(),
          }
        }),
    }

    if (type) {
      return typeMap[type] ?? []
    }
    return [
      ...typeMap.true_false,
      ...typeMap.multiple_choice,
      ...typeMap.matching,
      ...typeMap.checkbox,
    ]
  }

  async deleteKnowledgeTreeQuestion(
    _treeId: string,
    _chapter: number,
    _questionId: string
  ): Promise<void> {
    await delay(100)
  }

  async deleteAllKnowledgeTreeQuestions(_treeId: string, _chapter: number): Promise<void> {
    await delay(100)
  }

  async generateChapterFlashcards(_treeId: string, _chapter: number): Promise<{ task_id: string }> {
    await delay(200)
    return { task_id: 'mock-task-flashcards' }
  }

  async listChapterFlashcards(_treeId: string, _chapter: number): Promise<FlashcardOut[]> {
    await delay(200)
    return []
  }

  async deleteKnowledgeTreeFlashcard(_treeId: string, _chapter: number, _flashcardId: string): Promise<void> {
    await delay(100)
  }

  async deleteAllKnowledgeTreeFlashcards(_treeId: string, _chapter: number): Promise<void> {
    await delay(100)
  }

  // Exam Sessions
  private examSessions: ExamSession[] = []

  async saveExamSession(_treeId: string, _chapter: number, payload: CreateExamSessionPayload): Promise<ExamSession> {
    await delay(150)
    const session: ExamSession = {
      id: `mock-es-${Math.random().toString(36).slice(2, 10)}`,
      tree_id: _treeId,
      chapter_id: '',
      ...payload,
      score: payload.score,
      total_questions: payload.total_questions,
      correct_count: payload.correct_count,
      question_ids: payload.question_ids,
      results: payload.results,
      created_at: new Date().toISOString(),
    }
    this.examSessions.push(session)
    return session
  }

  async listExamSessions(_treeId: string, _chapter: number): Promise<ExamSession[]> {
    await delay(100)
    return [...this.examSessions].reverse()
  }

  async getExamSession(_treeId: string, _chapter: number, sessionId: string): Promise<ExamSession> {
    await delay(100)
    const session = this.examSessions.find((s) => s.id === sessionId)
    if (!session) throw new Error('Exam session not found')
    return session
  }

  // Study Sessions
  private studySessions: StudySession[] = []

  async saveStudySession(_treeId: string, _chapter: number, payload: CreateStudySessionPayload): Promise<StudySession> {
    await delay(150)
    const session: StudySession = {
      id: `mock-ss-${Math.random().toString(36).slice(2, 10)}`,
      tree_id: _treeId,
      chapter_id: '',
      total_cards: payload.total_cards,
      question_ids: payload.question_ids,
      created_at: new Date().toISOString(),
    }
    this.studySessions.push(session)
    return session
  }

  async listStudySessions(_treeId: string, _chapter: number): Promise<StudySession[]> {
    await delay(100)
    return [...this.studySessions].reverse()
  }

  async getStudySession(_treeId: string, _chapter: number, sessionId: string): Promise<StudySession> {
    await delay(100)
    const session = this.studySessions.find((s) => s.id === sessionId)
    if (!session) throw new Error('Study session not found')
    return session
  }

  // Provider credentials
  async listProviders(): Promise<ProviderInfo[]> {
    await delay(100)
    return [
      { slug: 'groq', label: 'Groq', key_required: true, models_endpoint: null, key_format_hint: 'gsk_...' },
      { slug: 'ollama', label: 'Ollama', key_required: false, models_endpoint: 'http://localhost:11434', key_format_hint: '' },
    ]
  }

  async listCredentials(): Promise<CredentialStatus[]> {
    await delay(100)
    return [
      { provider: 'groq', configured: false, last4: null, last_tested_at: null, last_test_ok: null, last_test_error: null },
      { provider: 'ollama', configured: true, last4: null, last_tested_at: null, last_test_ok: false, last_test_error: null },
    ]
  }

  async saveCredential(provider: string, apiKey: string): Promise<CredentialStatus> {
    await delay(150)
    return { provider, configured: true, last4: apiKey.slice(-4), last_tested_at: null, last_test_ok: true, last_test_error: null }
  }

  async deleteCredential(_provider: string): Promise<void> {
    await delay(100)
  }

  async testConnection(_provider: string, _apiKey?: string): Promise<TestConnectionResult> {
    await delay(300)
    return { ok: true, model_count: 5 }
  }

  // Auth
  async login(email: string, _password: string): Promise<AuthTokenResponse> {
    await delay(200)
    if (email === 'a@b.com') {
      return { access_token: 'mock-jwt-login', token_type: 'bearer', expires_in_days: 7 }
    }
    throw new Error('Invalid email or password')
  }

  async register(_email: string, _password: string, _displayName?: string): Promise<AuthTokenResponse> {
    await delay(200)
    return { access_token: 'mock-jwt-register', token_type: 'bearer', expires_in_days: 7 }
  }

  async getMe(): Promise<UserProfile> {
    await delay(100)
    return {
      id: 'mock-user-1',
      email: 'mock@example.com',
      display_name: 'Mock User',
      has_first_agent: false,
      created_at: new Date().toISOString(),
    }
  }

  async chat(_request: ChatRequest, _signal?: AbortSignal): Promise<ChatResponse> {
    await delay(500)
    return {
      reply: "This is a mock response. The AI assistant would answer your question here based on the document context provided."
    }
  }
}
