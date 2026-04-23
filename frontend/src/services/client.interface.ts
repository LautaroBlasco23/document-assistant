import type {
  HealthOut,
  ConfigOut,
  TaskStatusOut,
  ActiveTasksOut,
  DocumentPreviewOut,
  KnowledgeTreeQuestionType,
  KnowledgeTreeQuestionOut,
} from '../types/api'
import type { KnowledgeTree, KnowledgeChapter, KnowledgeDocument } from '../types/knowledge-tree'

export interface ServiceClient {
  health(): Promise<HealthOut>
  getConfig(): Promise<ConfigOut>
  getTaskStatus(taskId: string): Promise<TaskStatusOut>
  listActiveTasks(): Promise<ActiveTasksOut>

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
  createKnowledgeDocument(treeId: string, chapterId: string | null, title: string, content: string, isMain?: boolean): Promise<KnowledgeDocument>
  updateKnowledgeDocument(id: string, title: string, content: string): Promise<KnowledgeDocument>
  deleteKnowledgeDocument(id: string): Promise<void>
  ingestFileAsKnowledgeDocument(treeId: string, chapter: number, file: File): Promise<{ task_id: string }>
  previewKnowledgeTreeFile(file: File): Promise<DocumentPreviewOut>
  createKnowledgeTreeFromFile(file: File, title?: string, chapterIndices?: number[]): Promise<{ task_id: string }>

  // Document Reader
  getDocumentFileUrl(docId: string): string
  generateFlashcardFromSelection(treeId: string, chapter: number, selectedText: string): Promise<{ task_id: string }>

  // Knowledge Tree Questions
  generateKnowledgeTreeQuestions(
    treeId: string,
    chapter: number,
    questionTypes?: KnowledgeTreeQuestionType[]
  ): Promise<{ task_id: string }>

  getKnowledgeTreeQuestions(
    treeId: string,
    chapter: number,
    type?: KnowledgeTreeQuestionType
  ): Promise<KnowledgeTreeQuestionOut[]>

  deleteKnowledgeTreeQuestion(
    treeId: string,
    chapter: number,
    questionId: string
  ): Promise<void>
}

export type { ServiceClient as ServiceClientType }
