import type { DocumentOut, DocumentStructureOut } from '../types/api'

export const mockDocuments: DocumentOut[] = [
  {
    file_hash: 'a1b2c3d4e5f6',
    filename: 'Introduction to Machine Learning.pdf',
    num_chapters: 8,
  },
  {
    file_hash: 'd4e5f67890ab',
    filename: 'Clean Architecture.epub',
    num_chapters: 12,
  },
  {
    file_hash: 'g7h8i9j0k1l2',
    filename: 'The Art of War.pdf',
    num_chapters: 13,
  },
]

export const mockDocumentStructures: Record<string, DocumentStructureOut> = {
  'a1b2c3d4e5f6': {
    file_hash: 'a1b2c3d4e5f6',
    filename: 'Introduction to Machine Learning.pdf',
    chapters: [
      { number: 1, title: 'What is Machine Learning?', num_chunks: 12 },
      { number: 2, title: 'Supervised Learning', num_chunks: 18 },
      { number: 3, title: 'Unsupervised Learning', num_chunks: 14 },
      { number: 4, title: 'Neural Networks', num_chunks: 22 },
      { number: 5, title: 'Deep Learning', num_chunks: 20 },
      { number: 6, title: 'Model Evaluation', num_chunks: 10 },
      { number: 7, title: 'Feature Engineering', num_chunks: 16 },
      { number: 8, title: 'Practical Applications', num_chunks: 8 },
    ],
  },
  'd4e5f67890ab': {
    file_hash: 'd4e5f67890ab',
    filename: 'Clean Architecture.epub',
    chapters: [
      { number: 1, title: 'What is Design and Architecture?', num_chunks: 9 },
      { number: 2, title: 'A Tale of Two Values', num_chunks: 7 },
      { number: 3, title: 'Paradigm Overview', num_chunks: 11 },
      { number: 4, title: 'Structured Programming', num_chunks: 8 },
      { number: 5, title: 'Object-Oriented Programming', num_chunks: 13 },
      { number: 6, title: 'Functional Programming', num_chunks: 10 },
      { number: 7, title: 'The Dependency Rule', num_chunks: 15 },
      { number: 8, title: 'Use Cases', num_chunks: 12 },
      { number: 9, title: 'Clean Architecture Layers', num_chunks: 18 },
      { number: 10, title: 'Boundaries', num_chunks: 14 },
      { number: 11, title: 'The Main Component', num_chunks: 6 },
      { number: 12, title: 'Services: Great and Small', num_chunks: 9 },
    ],
  },
  'g7h8i9j0k1l2': {
    file_hash: 'g7h8i9j0k1l2',
    filename: 'The Art of War.pdf',
    chapters: [
      { number: 1, title: 'Laying Plans', num_chunks: 8 },
      { number: 2, title: 'Waging War', num_chunks: 6 },
      { number: 3, title: 'Attack by Stratagem', num_chunks: 7 },
      { number: 4, title: 'Tactical Dispositions', num_chunks: 5 },
      { number: 5, title: 'Energy', num_chunks: 6 },
      { number: 6, title: 'Weak Points and Strong', num_chunks: 9 },
      { number: 7, title: 'Maneuvering', num_chunks: 8 },
      { number: 8, title: 'Variation in Tactics', num_chunks: 5 },
      { number: 9, title: 'The Army on the March', num_chunks: 11 },
      { number: 10, title: 'Terrain', num_chunks: 9 },
      { number: 11, title: 'The Nine Situations', num_chunks: 14 },
      { number: 12, title: 'The Attack by Fire', num_chunks: 6 },
      { number: 13, title: 'The Use of Spies', num_chunks: 7 },
    ],
  },
}
