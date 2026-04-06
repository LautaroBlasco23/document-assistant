// Knowledge Tree domain types

export interface KnowledgeTree {
  id: string
  title: string
  description?: string
  num_chapters: number
  created_at: string
}

export interface KnowledgeChapter {
  id: string
  number: number
  title: string
  tree_id: string
}

export interface KnowledgeDocument {
  id: string
  tree_id: string
  chapter: number | null  // null = tree-level (main doc)
  title: string
  content: string
  is_main: boolean
  created_at: string
  updated_at: string
}

export type KnowledgeTreeTab = 'documents' | 'content'

// --- Exam question types ---

export interface TrueFalseQuestion {
  type: 'true-false'
  id: string
  statement: string
  answer: boolean
  explanation?: string
}

export interface MultipleChoiceQuestion {
  type: 'multiple-choice'
  id: string
  question: string
  choices: string[]
  correctIndex: number
  explanation?: string
}

export interface MatchingPair {
  term: string
  definition: string
}

export interface MatchingQuestion {
  type: 'matching'
  id: string
  prompt: string
  pairs: MatchingPair[]
}

export interface CheckboxQuestion {
  type: 'checkbox'
  id: string
  question: string
  choices: string[]
  correctIndices: number[]
  explanation?: string
}

export interface FlashcardQuestion {
  type: 'flashcard'
  id: string
  front: string
  back: string
}

export type ExamQuestion =
  | TrueFalseQuestion
  | MultipleChoiceQuestion
  | MatchingQuestion
  | CheckboxQuestion
  | FlashcardQuestion
