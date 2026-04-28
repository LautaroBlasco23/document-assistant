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
  status: 'pending' | 'running' | 'completed' | 'failed' | 'rate_limited'
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
  status: 'pending' | 'running' | 'completed' | 'failed' | 'rate_limited'
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

export interface FlashcardOut {
  id: string
  front: string
  back: string
  source_text: string | null
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
  model?: string
  agent_id?: string
}

export interface ModelInfo {
  id: string
  label: string
  role: string | null
}

export interface ModelsOut {
  provider: string
  current_model: string
  models: ModelInfo[]
}

export interface AgentOut {
  id: string
  name: string
  prompt: string
  model: string
  temperature: number
  top_p: number
  max_tokens: number
  is_default: boolean
  created_at: string
}

export interface CreateAgentRequest {
  name: string
  prompt?: string
  model: string
  temperature?: number
  top_p?: number
  max_tokens?: number
}

export interface UpdateAgentRequest {
  name?: string
  prompt?: string
  model?: string
  temperature?: number
  top_p?: number
  max_tokens?: number
}

export interface ChatRequest {
  messages: ChatMessage[]
  context?: string | null
  temperature?: number
  top_p?: number
  max_tokens?: number
  model?: string
  agent_id?: string
}

export interface ChatResponse {
  reply: string
}
