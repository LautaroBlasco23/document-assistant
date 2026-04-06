import * as React from 'react'
import { useNavigate } from 'react-router-dom'
import { TreePine, Layers, Trash2 } from 'lucide-react'
import { Card } from '../../components/ui/card'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import { Dialog } from '../../components/ui/dialog'
import type { KnowledgeTree } from '../../types/knowledge-tree'

interface KnowledgeTreeCardProps {
  tree: KnowledgeTree
  onDelete: (id: string) => void
}

export function KnowledgeTreeCard({ tree, onDelete }: KnowledgeTreeCardProps) {
  const navigate = useNavigate()
  const [deleteOpen, setDeleteOpen] = React.useState(false)

  return (
    <>
      <Card
        className="flex flex-col gap-3 hover:shadow-md transition-shadow cursor-pointer"
        onClick={() => navigate(`/trees/${tree.id}`)}
      >
        {/* Icon + title */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <TreePine className="h-4 w-4 text-green-600 shrink-0" />
            <span
              className="font-medium text-gray-800 truncate"
              title={tree.title}
            >
              {tree.title}
            </span>
          </div>
          <Badge variant="neutral" className="shrink-0">Tree</Badge>
        </div>

        {/* Description */}
        {tree.description && (
          <p className="text-xs text-gray-500 line-clamp-2">{tree.description}</p>
        )}

        {/* Stats */}
        <div className="flex items-center gap-4 text-xs text-gray-400">
          <span className="flex items-center gap-1">
            <Layers className="h-3.5 w-3.5" />
            {tree.num_chapters} {tree.num_chapters === 1 ? 'chapter' : 'chapters'}
          </span>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-1 border-t border-gray-100 mt-auto">
          <Button
            variant="primary"
            size="sm"
            onClick={(e) => { e.stopPropagation(); navigate(`/trees/${tree.id}`) }}
          >
            Open
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => { e.stopPropagation(); setDeleteOpen(true) }}
            className="text-red-500 hover:text-red-600 hover:bg-red-50"
            aria-label="Delete tree"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </Card>

      <Dialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete knowledge tree"
        description="This will permanently remove the tree and all its documents and chapters."
        onConfirm={() => onDelete(tree.id)}
        confirmLabel="Delete"
        variant="destructive"
      />
    </>
  )
}
