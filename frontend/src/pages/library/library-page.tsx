import * as React from 'react'
import { TreePine, Plus, Upload } from 'lucide-react'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import { SkeletonCard } from '../../components/ui/skeleton'
import { EmptyState } from '../../components/ui/empty-state'
import { useKnowledgeTreeStore } from '../../stores/knowledge-tree-store'
import { KnowledgeTreeCard } from './knowledge-tree-card'
import { CreateKnowledgeTreeDialog } from './create-knowledge-tree-dialog'
import { ImportTreeDialog } from './import-tree-dialog'

export function LibraryPage() {
  const { trees, treesLoading, fetchTrees, deleteTree } = useKnowledgeTreeStore()
  const [showCreateDialog, setShowCreateDialog] = React.useState(false)
  const [showImportDialog, setShowImportDialog] = React.useState(false)

  React.useEffect(() => {
    void fetchTrees()
  }, [fetchTrees])

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Knowledge Trees</h1>
        {trees.length > 0 && (
          <Badge variant="neutral">{trees.length}</Badge>
        )}
        <div className="ml-auto flex gap-2">
          <Button
            variant="secondary"
            onClick={() => setShowImportDialog(true)}
          >
            <Upload className="w-4 h-4 mr-1" />
            Import from Document
          </Button>
          <Button
            variant="secondary"
            onClick={() => setShowCreateDialog(true)}
          >
            <Plus className="w-4 h-4 mr-1" />
            New Tree
          </Button>
        </div>
      </div>

      <CreateKnowledgeTreeDialog
        open={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
      />

      <ImportTreeDialog
        open={showImportDialog}
        onOpenChange={setShowImportDialog}
        onSuccess={() => { /* navigation handled inside dialog */ }}
      />

      {treesLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : trees.length === 0 ? (
        <EmptyState
          icon={TreePine}
          title="No knowledge trees yet"
          description="Create a knowledge tree to organize documents by chapters and generate content from them."
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {trees.map((tree) => (
            <KnowledgeTreeCard
              key={tree.id}
              tree={tree}
              onDelete={(id) => void deleteTree(id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
