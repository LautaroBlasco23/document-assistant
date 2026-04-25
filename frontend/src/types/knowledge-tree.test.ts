/**
 * Subject: src/types/knowledge-tree.ts — mapApiQuestionToExamQuestion
 * Scope:   Mapping backend API question shapes to frontend ExamQuestion domain types.
 * Out of scope:
 *   - Question generation logic          → application agent tests
 *   - Component rendering of questions   → component tests
 * Setup:   None; pure function with inline fixtures.
 */

import { describe, it, expect } from 'vitest'
import { mapApiQuestionToExamQuestion } from './knowledge-tree'
import type { KnowledgeTreeQuestionOut } from './api'

describe('mapApiQuestionToExamQuestion', () => {
  // A well-formed true_false payload maps to the frontend TrueFalseQuestion shape.
  it('maps a well-formed true_false API question to a TrueFalseQuestion', () => {
    const apiQ: KnowledgeTreeQuestionOut = {
      id: 'tf-1',
      question_type: 'true_false',
      question_data: {
        statement: 'The sky is blue.',
        answer: true,
        explanation: 'Because of Rayleigh scattering.',
      },
      created_at: '2026-01-01T00:00:00Z',
    }
    const result = mapApiQuestionToExamQuestion(apiQ)
    expect(result).toEqual({
      type: 'true-false',
      id: 'tf-1',
      statement: 'The sky is blue.',
      answer: true,
      explanation: 'Because of Rayleigh scattering.',
    })
  })

  // A well-formed multiple_choice payload maps to the frontend MultipleChoiceQuestion shape.
  it('maps a well-formed multiple_choice API question to a MultipleChoiceQuestion', () => {
    const apiQ: KnowledgeTreeQuestionOut = {
      id: 'mc-1',
      question_type: 'multiple_choice',
      question_data: {
        question: 'What is 2+2?',
        choices: ['3', '4', '5'],
        correct_index: 1,
        explanation: 'Basic arithmetic.',
      },
      created_at: '2026-01-01T00:00:00Z',
    }
    const result = mapApiQuestionToExamQuestion(apiQ)
    expect(result).toEqual({
      type: 'multiple-choice',
      id: 'mc-1',
      question: 'What is 2+2?',
      choices: ['3', '4', '5'],
      correctIndex: 1,
      explanation: 'Basic arithmetic.',
    })
  })

  // A well-formed matching payload maps to the frontend MatchingQuestion shape.
  it('maps a well-formed matching API question to a MatchingQuestion', () => {
    const apiQ: KnowledgeTreeQuestionOut = {
      id: 'match-1',
      question_type: 'matching',
      question_data: {
        prompt: 'Match the terms.',
        pairs: [
          { term: 'A', definition: 'First letter' },
          { term: 'B', definition: 'Second letter' },
        ],
      },
      created_at: '2026-01-01T00:00:00Z',
    }
    const result = mapApiQuestionToExamQuestion(apiQ)
    expect(result).toEqual({
      type: 'matching',
      id: 'match-1',
      prompt: 'Match the terms.',
      pairs: [
        { term: 'A', definition: 'First letter' },
        { term: 'B', definition: 'Second letter' },
      ],
    })
  })

  // A well-formed checkbox payload maps to the frontend CheckboxQuestion shape.
  it('maps a well-formed checkbox API question to a CheckboxQuestion', () => {
    const apiQ: KnowledgeTreeQuestionOut = {
      id: 'cb-1',
      question_type: 'checkbox',
      question_data: {
        question: 'Select valid fruits.',
        choices: ['Apple', 'Carrot', 'Banana'],
        correct_indices: [0, 2],
      },
      created_at: '2026-01-01T00:00:00Z',
    }
    const result = mapApiQuestionToExamQuestion(apiQ)
    expect(result).toEqual({
      type: 'checkbox',
      id: 'cb-1',
      question: 'Select valid fruits.',
      choices: ['Apple', 'Carrot', 'Banana'],
      correctIndices: [0, 2],
    })
  })

  // The mapper does not recognise 'flashcard' as a valid API question type,
  // so it falls through to the default branch and returns null.
  it('returns null for a flashcard question because it is not a supported API type', () => {
    const apiQ: KnowledgeTreeQuestionOut = {
      id: 'fc-1',
      question_type: 'flashcard' as any,
      question_data: { front: 'Hello', back: 'World' },
      created_at: '2026-01-01T00:00:00Z',
    }
    const result = mapApiQuestionToExamQuestion(apiQ)
    expect(result).toBeNull()
  })

  // Missing required fields (statement for true_false) causes the mapper to bail out with null.
  it('returns null when required true_false fields are missing', () => {
    const apiQ: KnowledgeTreeQuestionOut = {
      id: 'tf-bad',
      question_type: 'true_false',
      question_data: { answer: true }, // missing statement
      created_at: '2026-01-01T00:00:00Z',
    }
    expect(mapApiQuestionToExamQuestion(apiQ)).toBeNull()
  })

  // Missing correct_index for multiple_choice triggers the null guard.
  it('returns null when required multiple_choice fields are missing', () => {
    const apiQ: KnowledgeTreeQuestionOut = {
      id: 'mc-bad',
      question_type: 'multiple_choice',
      question_data: { question: 'What?', choices: ['A'] }, // missing correct_index
      created_at: '2026-01-01T00:00:00Z',
    }
    expect(mapApiQuestionToExamQuestion(apiQ)).toBeNull()
  })

  // An unrecognised question_type string falls through the switch and returns null.
  it('returns null for an unknown question type', () => {
    const apiQ: KnowledgeTreeQuestionOut = {
      id: 'unknown-1',
      question_type: 'open_ended' as any,
      question_data: { text: 'Explain.' },
      created_at: '2026-01-01T00:00:00Z',
    }
    expect(mapApiQuestionToExamQuestion(apiQ)).toBeNull()
  })
})
