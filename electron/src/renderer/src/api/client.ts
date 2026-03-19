import axios, { AxiosInstance } from 'axios'

const API_BASE_URL = 'http://localhost:8000/api'

const client: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export default client

// Type-safe API wrapper functions
export const api = {
  health: () => client.get('/health'),
  listDocuments: () => client.get('/documents'),
  documentStructure: (hash: string) => client.get(`/documents/${hash}/structure`),
  deleteDocument: (hash: string) => client.delete(`/documents/${hash}`),
  ingestDocument: (formData: FormData) =>
    client.post('/documents/ingest', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }),
  search: (query: string, k: number = 20, chapter?: number) =>
    client.post('/search', { query, k, chapter }),
  ask: (query: string, chapter?: number) =>
    client.post('/ask', { query, chapter }),
  getConfig: () => client.get('/config'),
  updateConfig: (config: Record<string, unknown>) => client.put('/config', config),
  getTaskStatus: (taskId: string) => client.get(`/tasks/${taskId}`),
  summarizeChapter: (chapter: number, bookTitle: string) =>
    client.post('/chapters/summarize', { chapter, book_title: bookTitle }),
  generateQA: (chapter: number, bookTitle: string) =>
    client.post('/chapters/questions', { chapter, book_title: bookTitle }),
  generateFlashcards: (chapter: number, bookTitle: string) =>
    client.post('/chapters/flashcards', { chapter, book_title: bookTitle }),
}
