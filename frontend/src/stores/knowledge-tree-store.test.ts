/**
 * Subject: src/stores/knowledge-tree-store.ts — useKnowledgeTreeStore
 * Scope:   CRUD for trees, chapters, documents; question generation & retrieval;
 *          file ingest workflows
 * Out of scope:
 *   - Error-toast stack         → app-store.test.ts
 *   - Background task polling   → task-store.test.ts
 * Setup:   Zustand store reset; @/services/index fully mocked.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import type {
  KnowledgeTree,
  KnowledgeChapter,
  KnowledgeDocument,
} from '../types/knowledge-tree'
import type { KnowledgeTreeQuestionOut } from '../types/api'

vi.mock('@/services/index', () => ({
  client: {
    listKnowledgeTrees: vi.fn(),
    createKnowledgeTree: vi.fn(),
    updateKnowledgeTree: vi.fn(),
    deleteKnowledgeTree: vi.fn(),
    getKnowledgeTreeChapters: vi.fn(),
    createKnowledgeChapter: vi.fn(),
    updateKnowledgeChapter: vi.fn(),
    deleteKnowledgeChapter: vi.fn(),
    listKnowledgeDocuments: vi.fn(),
    createKnowledgeDocument: vi.fn(),
    updateKnowledgeDocument: vi.fn(),
    deleteKnowledgeDocument: vi.fn(),
    ingestFileAsKnowledgeDocument: vi.fn(),
    createKnowledgeTreeFromFile: vi.fn(),
    generateKnowledgeTreeQuestions: vi.fn(),
    getKnowledgeTreeQuestions: vi.fn(),
    deleteKnowledgeTreeQuestion: vi.fn(),
  },
}))

import { client } from '@/services/index'
import { useKnowledgeTreeStore } from './knowledge-tree-store'

const mockClient = vi.mocked(client, true)

describe('useKnowledgeTreeStore', () => {
  beforeEach(() => {
    useKnowledgeTreeStore.setState({
      trees: [],
      treesLoading: false,
      treesFetched: false,
      chapters: {},
      chaptersLoading: {},
      documents: {},
      documentsLoading: {},
      questionsByType: {},
      questionsLoading: {},
      questionTaskIds: {},
    })
    vi.clearAllMocks()
  })

  // fetchTrees loads the list from the API and records that data has been fetched.
  it('fetchTrees populates trees and sets treesFetched', async () => {
    const trees: KnowledgeTree[] = [
      { id: '1', title: 'B', num_chapters: 0, created_at: '2024-01-01' },
      { id: '2', title: 'A', num_chapters: 1, created_at: '2024-01-02' },
    ]
    mockClient.listKnowledgeTrees.mockResolvedValue(trees)

    await useKnowledgeTreeStore.getState().fetchTrees()

    const state = useKnowledgeTreeStore.getState()
    expect(state.trees).toEqual(trees)
    expect(state.treesFetched).toBe(true)
    expect(state.treesLoading).toBe(false)
  })

  // createTree appends the new tree to the local array and returns it.
  it('createTree adds tree and returns it', async () => {
    const tree: KnowledgeTree = {
      id: '1',
      title: 'New',
      num_chapters: 0,
      created_at: '2024-01-01',
    }
    mockClient.createKnowledgeTree.mockResolvedValue(tree)

    const result = await useKnowledgeTreeStore.getState().createTree('New')

    expect(result).toEqual(tree)
    expect(useKnowledgeTreeStore.getState().trees).toContainEqual(tree)
  })

  // updateTree replaces the matching tree in place and returns the updated value.
  it('updateTree modifies title and description', async () => {
    const existing: KnowledgeTree = {
      id: '1',
      title: 'Old',
      description: 'desc',
      num_chapters: 0,
      created_at: '2024-01-01',
    }
    useKnowledgeTreeStore.setState({ trees: [existing] })
    const updated: KnowledgeTree = {
      id: '1',
      title: 'New',
      description: 'new desc',
      num_chapters: 0,
      created_at: '2024-01-01',
    }
    mockClient.updateKnowledgeTree.mockResolvedValue(updated)

    const result = await useKnowledgeTreeStore.getState().updateTree(
      '1',
      'New',
      'new desc',
    )

    expect(result).toEqual(updated)
    expect(useKnowledgeTreeStore.getState().trees[0].title).toBe('New')
    expect(useKnowledgeTreeStore.getState().trees[0].description).toBe('new desc')
  })

  // deleteTree removes only the tree with the matching id.
  it('deleteTree removes from array', async () => {
    const trees: KnowledgeTree[] = [
      { id: '1', title: 'A', num_chapters: 0, created_at: '2024-01-01' },
      { id: '2', title: 'B', num_chapters: 0, created_at: '2024-01-02' },
    ]
    useKnowledgeTreeStore.setState({ trees })
    mockClient.deleteKnowledgeTree.mockResolvedValue(undefined)

    await useKnowledgeTreeStore.getState().deleteTree('1')

    expect(useKnowledgeTreeStore.getState().trees).toHaveLength(1)
    expect(useKnowledgeTreeStore.getState().trees[0].id).toBe('2')
  })

  // fetchChapters stores the chapter list under the treeId key.
  it('fetchChapters populates chapters keyed by treeId', async () => {
    const chapters: KnowledgeChapter[] = [
      { id: 'c1', number: 1, title: 'Ch1', tree_id: 't1' },
      { id: 'c2', number: 2, title: 'Ch2', tree_id: 't1' },
    ]
    mockClient.getKnowledgeTreeChapters.mockResolvedValue(chapters)

    await useKnowledgeTreeStore.getState().fetchChapters('t1')

    expect(useKnowledgeTreeStore.getState().chapters['t1']).toEqual(chapters)
    expect(useKnowledgeTreeStore.getState().chaptersLoading['t1']).toBe(false)
  })

  // createChapter appends to the chapter array and bumps the tree's num_chapters.
  it('createChapter adds chapter and increments num_chapters', async () => {
    const tree: KnowledgeTree = {
      id: 't1',
      title: 'Tree',
      num_chapters: 1,
      created_at: '2024-01-01',
    }
    useKnowledgeTreeStore.setState({
      trees: [tree],
      chapters: {
        t1: [{ id: 'c1', number: 1, title: 'Ch1', tree_id: 't1' }],
      },
    })
    const newChapter: KnowledgeChapter = {
      id: 'c2',
      number: 2,
      title: 'Ch2',
      tree_id: 't1',
    }
    mockClient.createKnowledgeChapter.mockResolvedValue(newChapter)

    const result = await useKnowledgeTreeStore.getState().createChapter('t1', 'Ch2')

    expect(result).toEqual(newChapter)
    expect(useKnowledgeTreeStore.getState().chapters['t1']).toHaveLength(2)
    expect(useKnowledgeTreeStore.getState().trees[0].num_chapters).toBe(2)
  })

  // updateChapter swaps the matching chapter by number and returns the new value.
  it('updateChapter modifies chapter title', async () => {
    const chapters: KnowledgeChapter[] = [
      { id: 'c1', number: 1, title: 'Old', tree_id: 't1' },
    ]
    useKnowledgeTreeStore.setState({ chapters: { t1: chapters } })
    const updated: KnowledgeChapter = {
      id: 'c1',
      number: 1,
      title: 'New',
      tree_id: 't1',
    }
    mockClient.updateKnowledgeChapter.mockResolvedValue(updated)

    const result = await useKnowledgeTreeStore.getState().updateChapter('t1', 1, 'New')

    expect(result).toEqual(updated)
    expect(useKnowledgeTreeStore.getState().chapters['t1'][0].title).toBe('New')
  })

  // deleteChapter drops the chapter with the given number and decrements the tree count.
  it('deleteChapter removes chapter', async () => {
    const chapters: KnowledgeChapter[] = [
      { id: 'c1', number: 1, title: 'Ch1', tree_id: 't1' },
      { id: 'c2', number: 2, title: 'Ch2', tree_id: 't1' },
    ]
    const tree: KnowledgeTree = {
      id: 't1',
      title: 'Tree',
      num_chapters: 2,
      created_at: '2024-01-01',
    }
    useKnowledgeTreeStore.setState({ chapters: { t1: chapters }, trees: [tree] })
    mockClient.deleteKnowledgeChapter.mockResolvedValue(undefined)

    await useKnowledgeTreeStore.getState().deleteChapter('t1', 1)

    expect(useKnowledgeTreeStore.getState().chapters['t1']).toHaveLength(1)
    expect(useKnowledgeTreeStore.getState().chapters['t1'][0].number).toBe(2)
    expect(useKnowledgeTreeStore.getState().trees[0].num_chapters).toBe(1)
  })

  // fetchDocuments stores documents under the composite key treeId:chapter.
  it('fetchDocuments populates documents', async () => {
    const docs: KnowledgeDocument[] = [
      {
        id: 'd1',
        tree_id: 't1',
        chapter_id: null,
        chapter_number: null,
        title: 'Doc1',
        content: 'c1',
        is_main: true,
        created_at: '2024-01-01',
        updated_at: '2024-01-01',
      },
    ]
    mockClient.listKnowledgeDocuments.mockResolvedValue(docs)

    await useKnowledgeTreeStore.getState().fetchDocuments('t1', null, null)

    expect(useKnowledgeTreeStore.getState().documents['t1:main']).toEqual(docs)
    expect(useKnowledgeTreeStore.getState().documentsLoading['t1:main']).toBe(false)
  })

  // createDocument appends the new doc to the correct chapter bucket.
  it('createDocument adds document', async () => {
    useKnowledgeTreeStore.setState({ chapters: { t1: [] } })
    const doc: KnowledgeDocument = {
      id: 'd1',
      tree_id: 't1',
      chapter_id: null,
      chapter_number: null,
      title: 'Doc1',
      content: 'c1',
      is_main: false,
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    }
    mockClient.createKnowledgeDocument.mockResolvedValue(doc)

    const result = await useKnowledgeTreeStore.getState().createDocument(
      't1',
      null,
      'Doc1',
      'c1',
    )

    expect(result).toEqual(doc)
    expect(useKnowledgeTreeStore.getState().documents['t1:main']).toContainEqual(doc)
  })

  // updateDocument replaces the matching document in the local bucket.
  it('updateDocument modifies content', async () => {
    const existing: KnowledgeDocument = {
      id: 'd1',
      tree_id: 't1',
      chapter_id: null,
      chapter_number: null,
      title: 'Old',
      content: 'old',
      is_main: false,
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    }
    useKnowledgeTreeStore.setState({ documents: { 't1:main': [existing] } })
    const updated: KnowledgeDocument = {
      id: 'd1',
      tree_id: 't1',
      chapter_id: null,
      chapter_number: null,
      title: 'New',
      content: 'new',
      is_main: false,
      created_at: '2024-01-01',
      updated_at: '2024-01-02',
    }
    mockClient.updateKnowledgeDocument.mockResolvedValue(updated)

    const result = await useKnowledgeTreeStore.getState().updateDocument(
      'd1',
      'New',
      'new',
      't1',
      null,
    )

    expect(result).toEqual(updated)
    expect(useKnowledgeTreeStore.getState().documents['t1:main'][0].content).toBe('new')
  })

  // deleteDocument filters out only the document with the matching id.
  it('deleteDocument removes document', async () => {
    const docs: KnowledgeDocument[] = [
      {
        id: 'd1',
        tree_id: 't1',
        chapter_id: null,
        chapter_number: null,
        title: 'Doc1',
        content: 'c1',
        is_main: true,
        created_at: '2024-01-01',
        updated_at: '2024-01-01',
      },
      {
        id: 'd2',
        tree_id: 't1',
        chapter_id: null,
        chapter_number: null,
        title: 'Doc2',
        content: 'c2',
        is_main: false,
        created_at: '2024-01-01',
        updated_at: '2024-01-01',
      },
    ]
    useKnowledgeTreeStore.setState({ documents: { 't1:main': docs } })
    mockClient.deleteKnowledgeDocument.mockResolvedValue(undefined)

    await useKnowledgeTreeStore.getState().deleteDocument('d1', 't1', null)

    expect(useKnowledgeTreeStore.getState().documents['t1:main']).toHaveLength(1)
    expect(useKnowledgeTreeStore.getState().documents['t1:main'][0].id).toBe('d2')
  })

  // ingestFileAsDocument proxies to the client and returns the task id wrapper.
  it('ingestFileAsDocument returns task_id', async () => {
    mockClient.ingestFileAsKnowledgeDocument.mockResolvedValue({
      task_id: 'task-123',
    })
    const file = new File([], 'test.pdf')

    const result = await useKnowledgeTreeStore.getState().ingestFileAsDocument(
      't1',
      1,
      file,
    )

    expect(result).toEqual({ task_id: 'task-123' })
  })

  // createTreeFromFile proxies to the client and extracts the task id string.
  it('createTreeFromFile returns task_id', async () => {
    mockClient.createKnowledgeTreeFromFile.mockResolvedValue({
      task_id: 'task-456',
    })
    const file = new File([], 'test.pdf')

    const result = await useKnowledgeTreeStore.getState().createTreeFromFile(
      file,
      'Title',
    )

    expect(result).toBe('task-456')
  })

  // generateQuestions records the returned task id under the composite key.
  it('generateQuestions stores task_id', async () => {
    mockClient.generateKnowledgeTreeQuestions.mockResolvedValue({
      task_id: 'task-q',
    })

    const result = await useKnowledgeTreeStore.getState().generateQuestions(
      't1',
      1,
      'true_false',
    )

    expect(result).toBe('task-q')
    expect(
      useKnowledgeTreeStore.getState().questionTaskIds['t1:1:true_false'],
    ).toBe('task-q')
  })

  // fetchQuestions maps raw API questions into the frontend ExamQuestion buckets by type.
  it('fetchQuestions populates questionsByType', async () => {
    const raw: KnowledgeTreeQuestionOut[] = [
      {
        id: 'q1',
        question_type: 'true_false',
        question_data: { statement: 'S', answer: true },
        created_at: '2024-01-01',
      },
      {
        id: 'q2',
        question_type: 'multiple_choice',
        question_data: { question: 'Q', choices: ['a', 'b'], correct_index: 0 },
        created_at: '2024-01-01',
      },
    ]
    mockClient.getKnowledgeTreeQuestions.mockResolvedValue(raw)

    await useKnowledgeTreeStore.getState().fetchQuestions('t1', 1)

    const byType = useKnowledgeTreeStore.getState().questionsByType['t1:1']
    expect(byType?.true_false).toHaveLength(1)
    expect(byType?.multiple_choice).toHaveLength(1)
    expect(byType?.true_false?.[0].type).toBe('true-false')
    expect(byType?.multiple_choice?.[0].type).toBe('multiple-choice')
  })

  // deleteQuestion removes the question locally and then triggers a server refetch.
  it('deleteQuestion removes question and refetches', async () => {
    const questions = [
      { type: 'true-false' as const, id: 'q1', statement: 'S1', answer: true },
      { type: 'true-false' as const, id: 'q2', statement: 'S2', answer: false },
    ]
    useKnowledgeTreeStore.setState({
      questionsByType: { 't1:1': { true_false: questions } },
    })
    mockClient.deleteKnowledgeTreeQuestion.mockResolvedValue(undefined)
    mockClient.getKnowledgeTreeQuestions.mockResolvedValue([
      {
        id: 'q2',
        question_type: 'true_false',
        question_data: { statement: 'S2', answer: false },
        created_at: '2024-01-01',
      },
    ])

    await useKnowledgeTreeStore.getState().deleteQuestion('t1', 1, 'q1')

    // Allow the fire-and-forget refetch to settle.
    await new Promise((r) => setTimeout(r, 0))

    const byType = useKnowledgeTreeStore.getState().questionsByType['t1:1']
    expect(byType?.true_false).toHaveLength(1)
    expect(byType?.true_false?.[0].id).toBe('q2')
    expect(mockClient.deleteKnowledgeTreeQuestion).toHaveBeenCalledWith('t1', 1, 'q1')
    expect(mockClient.getKnowledgeTreeQuestions).toHaveBeenCalledWith('t1', 1)
  })
})
