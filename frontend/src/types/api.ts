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
  title?: string
  num_chunks: number
  sections?: SectionOut[]
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
  front: string
  back: string
  category?: 'terminology' | 'key_facts' | 'concepts'
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
  created_at: string
}

export interface OllamaConfig {
  base_url: string
  generation_model: string
  embedding_model: string
  timeout: number
}

export interface QdrantConfig {
  url: string
  collection_name: string
}

export interface Neo4jConfig {
  uri: string
  user: string
}

export interface ChunkingConfig {
  max_tokens: number
  overlap_tokens: number
}

export interface ConfigOut {
  ollama: OllamaConfig
  qdrant: QdrantConfig
  neo4j: Neo4jConfig
  chunking: ChunkingConfig
}

export interface MetadataResponse {
  document_hash: string
  description: string
  document_type: string
}
