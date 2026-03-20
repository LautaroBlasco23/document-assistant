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

export interface ChapterOut {
  number: number
  title?: string
  num_chunks: number
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

export interface SearchRequest {
  query: string
  book?: string
  chapter?: number
  k: number
}

export interface ChunkOut {
  id: string
  text: string
  chapter: number
  page?: number
  score?: number
}

export interface SearchResultsOut {
  query: string
  chunks: ChunkOut[]
  count: number
}

export interface AskRequest {
  query: string
  book?: string
  chapter?: number
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
  result?: Record<string, unknown>
  error?: string
}

export interface SummaryOut {
  chapter: number
  summary: string
}

export interface QAPairOut {
  question: string
  answer: string
}

export interface FlashcardOut {
  question: string
  answer: string
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
