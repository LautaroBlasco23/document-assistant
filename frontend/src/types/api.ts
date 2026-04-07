// TypeScript interfaces mirroring all backend Pydantic schemas

export interface ServiceStatus {
  name: string
  healthy: boolean
  error?: string
}

export interface HealthOut {
  status: string
  services: ServiceStatus[]
}

export interface SectionOut {
  title: string
  page_start: number
  page_end: number
}

export interface ChapterOut {
  number: number
  chapter_index: number
  title?: string
  num_chunks: number
  sections?: SectionOut[]
  toc_href?: string
}

export interface DocumentOut {
  file_hash: string
  filename: string
  num_chapters: number
  chapters?: ChapterOut[]
}

export interface DocumentStructureOut {
  file_hash: string
  filename: string
  num_chapters: number
  chapters: ChapterOut[]
}

export interface IngestTaskOut {
  task_id: string
  filename: string
}

export interface ChapterRequest {
  book_title: string
  chapter: number
}

export interface TaskResponseOut {
  task_id: string
  task_type: string
}

export interface TaskStatusOut {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: string
  progress_pct?: number
  result?: Record<string, unknown>
  error?: string
}

export interface SummaryOut {
  chapter: number
  description: string
  bullets: string[]
}

export interface FlashcardOut {
  id?: string
  front: string
  back: string
  category?: 'terminology' | 'key_facts' | 'concepts'
  source_page?: number
  source_chunk_id?: string
  source_text?: string
}

// Stored content responses (from PostgreSQL via GET endpoints)
export interface SummaryResponse {
  chapter: number  // 1-based
  content: string
  description: string
  bullets: string[]
  created_at: string
}

export interface FlashcardResponse {
  id: string
  chapter: number  // 1-based
  front: string
  back: string
  source_page: number | null
  source_chunk_id: string
  source_text: string
  status: 'pending' | 'approved'
  created_at: string
}

export interface OllamaConfig {
  base_url: string
  generation_model: string
  timeout: number
}

export interface ChunkingConfig {
  max_tokens: number
  overlap_tokens: number
}

export interface ConfigOut {
  ollama: OllamaConfig
  chunking: ChunkingConfig
}

export interface MetadataResponse {
  document_hash: string
  description: string
  document_type: string
  file_extension: string
}

export interface ChapterDeleteResponse {
  message: string
  chunks_deleted: number
  summaries_deleted: number
  flashcards_deleted: number
}

export interface ActiveTaskOut {
  task_id: string
  task_type: string
  doc_hash: string
  filename: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: string
  progress_pct: number
  chapter: number
  book_title: string
}

export interface ActiveTasksOut {
  tasks: ActiveTaskOut[]
}

export interface ChapterPreviewOut {
  index: number
  title: string
  page_start: number
  page_end: number
}

export interface DocumentPreviewOut {
  file_hash: string
  filename: string
  num_chapters: number
  chapters: ChapterPreviewOut[]
}

export interface IngestChaptersRequest {
  chapter_indices: number[]
  document_type?: string
  description?: string
}

export interface ExamResultOut {
  id: string
  chapter: number         // 1-based
  total_cards: number
  correct_count: number
  passed: boolean
  completed_at: string    // ISO 8601
}

export interface ChapterExamStatusOut {
  chapter: number         // 1-based
  level: number           // 0-3
  level_name: string      // "none" | "completed" | "gold" | "platinum"
  last_exam_at: string | null
  cooldown_until: string | null
  can_take_exam: boolean
}

export interface CreateDocumentRequest {
  title: string
  content: string
  description?: string
  document_type?: string
}

export interface CreateDocumentResponse {
  task_id: string
  file_hash: string
  title: string
}

export interface AppendContentRequest {
  content: string
}

export interface AppendContentResponse {
  task_id: string
  file_hash: string
}

export interface DocumentContentResponse {
  content: string
  num_chapters: number
}

export interface UpdateContentResponse {
  same: boolean
  new_hash?: string
  task_id?: string
  preserved?: { summaries: number; flashcards: number }
}
