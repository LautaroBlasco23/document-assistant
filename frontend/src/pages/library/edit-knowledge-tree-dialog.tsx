import * as React from 'react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { useKnowledgeTreeStore } from '../../stores/knowledge-tree-store'
import type { KnowledgeTree } from '../../types/knowledge-tree'

interface EditKnowledgeTreeDialogProps {
  tree: KnowledgeTree
  open: boolean
  onClose: () => void
}

export function EditKnowledgeTreeDialog({ tree, open, onClose }: EditKnowledgeTreeDialogProps) {
  const [title, setTitle] = React.useState(tree.title)
  const [description, setDescription] = React.useState(tree.description ?? '')
  const [loading, setLoading] = React.useState(false)
  const updateTree = useKnowledgeTreeStore((s) => s.updateTree)

  // Sync with tree prop when dialog opens
  React.useEffect(() => {
    if (open) {
      setTitle(tree.title)
      setDescription(tree.description ?? '')
    }
  }, [open, tree.title, tree.description])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    setLoading(true)
    try {
      await updateTree(tree.id, title.trim(), description.trim() || undefined)
      onClose()
    } finally {
      setLoading(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-surface dark:bg-surface-200 rounded-xl shadow-xl w-full max-w-md mx-4 p-6 flex flex-col gap-5">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100">Edit Knowledge Tree</h2>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">Update the title and description.</p>
        </div>

        <form onSubmit={(e) => void handleSubmit(e)} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="edit-tree-title" className="text-sm font-medium text-gray-700 dark:text-slate-300">
              Title <span className="text-red-400">*</span>
            </label>
            <Input
              id="edit-tree-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              autoFocus
              required
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="edit-tree-description" className="text-sm font-medium text-gray-700 dark:text-slate-300">
              Description <span className="text-gray-400 dark:text-slate-500 font-normal">(optional)</span>
            </label>
            <textarea
              id="edit-tree-description"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full rounded-md border border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 px-3 py-2 text-sm text-gray-700 dark:text-slate-100 placeholder-gray-400 dark:placeholder-slate-500 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary resize-none"
            />
          </div>

          <div className="flex gap-2 justify-end pt-1">
            <Button type="button" variant="secondary" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={!title.trim() || loading}>
              {loading ? 'Saving...' : 'Save'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
