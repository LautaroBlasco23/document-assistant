// Knowledge Tree domain types

export interface KnowledgeTree {
  id: string
  title: string
  description?: string
  num_chapters: number
  created_at: string
}

export interface KnowledgeChapter {
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
