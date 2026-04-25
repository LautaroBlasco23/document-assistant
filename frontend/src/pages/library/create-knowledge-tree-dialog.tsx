import * as React from 'react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { useKnowledgeTreeStore } from '../../stores/knowledge-tree-store'

interface CreateKnowledgeTreeDialogProps {
  open: boolean
  onClose: () => void
}

export function CreateKnowledgeTreeDialog({ open, onClose }: CreateKnowledgeTreeDialogProps) {
  const [title, setTitle] = React.useState('')
  const [description, setDescription] = React.useState('')
  const [loading, setLoading] = React.useState(false)
  const createTree = useKnowledgeTreeStore((s) => s.createTree)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    setLoading(true)
    try {
      await createTree(title.trim(), description.trim() || undefined)
      setTitle('')
      setDescription('')
      onClose()
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setTitle('')
    setDescription('')
    onClose()
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-xl w-full max-w-md mx-4 p-6 flex flex-col gap-5">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-slate-100">New Knowledge Tree</h2>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
            A knowledge tree organizes documents by chapters. Content is generated from those documents.
          </p>
        </div>

        <form onSubmit={(e) => void handleSubmit(e)} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="tree-title" className="text-sm font-medium text-gray-700 dark:text-slate-300">
              Title <span className="text-red-400">*</span>
            </label>
            <Input
              id="tree-title"
              placeholder="e.g. Machine Learning Fundamentals"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              autoFocus
              required
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="tree-description" className="text-sm font-medium text-gray-700 dark:text-slate-300">
              Description <span className="text-gray-400 dark:text-slate-500 font-normal">(optional)</span>
            </label>
            <textarea
              id="tree-description"
              rows={3}
              placeholder="What is this knowledge tree about?"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full rounded-md border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-2 text-sm text-gray-700 dark:text-slate-100 placeholder-gray-400 dark:placeholder-slate-500 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary resize-none"
            />
          </div>

          <div className="flex gap-2 justify-end pt-1">
            <Button type="button" variant="secondary" onClick={handleClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={!title.trim() || loading}>
              {loading ? 'Creating...' : 'Create Tree'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
