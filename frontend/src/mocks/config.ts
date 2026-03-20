import type { ConfigOut } from '../types/api'

export const mockConfig: ConfigOut = {
  ollama: {
    base_url: 'http://localhost:11434',
    generation_model: 'llama3.2',
    embedding_model: 'nomic-embed-text',
    timeout: 120,
  },
  qdrant: {
    url: 'http://localhost:6333',
    collection_name: 'document_chunks',
  },
  neo4j: {
    uri: 'bolt://localhost:7687',
    user: 'neo4j',
  },
  chunking: {
    max_tokens: 512,
    overlap_tokens: 64,
  },
}
