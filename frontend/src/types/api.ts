// TypeScript interfaces mirroring backend Pydantic schemas

export interface ServiceStatus {
  name: string
  healthy: boolean
  error?: string
}

export interface HealthOut {
  status: string
  services: ServiceStatus[]
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

export type KnowledgeTreeQuestionType =
  | 'true_false'
  | 'multiple_choice'
  | 'matching'
  | 'checkbox'

export interface KnowledgeTreeQuestionOut {
  id: string
  question_type: KnowledgeTreeQuestionType
  question_data: Record<string, unknown>
  created_at: string
}

export interface ChatMessage {
  role: string
  content: string
}

export interface GenerationParams {
  temperature: number
  top_p: number
  max_tokens: number
}

export interface ChatRequest {
  messages: ChatMessage[]
  context?: string | null
  temperature?: number
  top_p?: number
  max_tokens?: number
}

export interface ChatResponse {
  reply: string
}
