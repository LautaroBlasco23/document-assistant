import type { ConfigOut } from '../types/api'

export const mockConfig: ConfigOut = {
  ollama: {
    base_url: 'http://localhost:11434',
    generation_model: 'llama3.2',
    timeout: 120,
  },
  chunking: {
    max_tokens: 512,
    overlap_tokens: 64,
  },
}
