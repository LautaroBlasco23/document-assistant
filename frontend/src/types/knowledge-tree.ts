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

// ---------------------------------------------------------------------------
// API mapper — converts backend snake_case shapes to frontend camelCase types
// ---------------------------------------------------------------------------

import type { KnowledgeTreeQuestionOut } from './api'

export function mapApiQuestionToExamQuestion(q: KnowledgeTreeQuestionOut): ExamQuestion | null {
  const d = q.question_data
  switch (q.question_type) {
    case 'true_false':
      if (typeof d.statement !== 'string' || typeof d.answer !== 'boolean') return null
      return {
        type: 'true-false',
        id: q.id,
        statement: d.statement,
        answer: d.answer,
        explanation: typeof d.explanation === 'string' ? d.explanation : undefined,
      }
    case 'multiple_choice':
      if (
        typeof d.question !== 'string' ||
        !Array.isArray(d.choices) ||
        typeof d.correct_index !== 'number'
      ) return null
      return {
        type: 'multiple-choice',
        id: q.id,
        question: d.question as string,
        choices: d.choices as string[],
        correctIndex: d.correct_index as number,
        explanation: typeof d.explanation === 'string' ? d.explanation : undefined,
      }
    case 'matching':
      if (typeof d.prompt !== 'string' || !Array.isArray(d.pairs)) return null
      return {
        type: 'matching',
        id: q.id,
        prompt: d.prompt as string,
        pairs: d.pairs as MatchingPair[],
      }
    case 'checkbox':
      if (
        typeof d.question !== 'string' ||
        !Array.isArray(d.choices) ||
        !Array.isArray(d.correct_indices)
      ) return null
      return {
        type: 'checkbox',
        id: q.id,
        question: d.question as string,
        choices: d.choices as string[],
        correctIndices: d.correct_indices as number[],
        explanation: typeof d.explanation === 'string' ? d.explanation : undefined,
      }
    default:
      return null
  }
}
