import * as React from 'react'
import { FileUp, Plus } from 'lucide-react'
import { Badge } from '../../components/ui/badge'
import { Button } from '../../components/ui/button'
import { SkeletonCard } from '../../components/ui/skeleton'
import { EmptyState } from '../../components/ui/empty-state'
import { useDocuments } from '../../hooks/use-documents'
import { useDocumentStore } from '../../stores/document-store'
import { useUploadStore } from '../../stores/upload-store'
import { UploadZone } from './upload-zone'
import { DocumentCard } from './document-card'
import { UploadingDocumentCard } from './uploading-document-card'
import { CreateDocumentDialog } from '../../components/dialogs/create-document-dialog'

export function LibraryPage() {
  const { documents, loading } = useDocuments()
  const removeDocument = useDocumentStore((state) => state.removeDocument)
  const uploads = useUploadStore((state) => state.uploads)
  const dismissUpload = useUploadStore((state) => state.dismissUpload)
  const [showCreateDialog, setShowCreateDialog] = React.useState(false)

  const hasContent = documents.length > 0 || uploads.length > 0

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Library</h1>
        {documents.length > 0 && (
          <Badge variant="neutral">{documents.length}</Badge>
        )}
        <div className="ml-auto">
          <Button
            variant="secondary"
            onClick={() => setShowCreateDialog(true)}
          >
            <Plus className="w-4 h-4 mr-1" />
            Create Document
          </Button>
        </div>
      </div>

      {/* Upload zone */}
      <UploadZone />

      <CreateDocumentDialog
        open={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
      />

      {/* Document grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : !hasContent ? (
        <EmptyState
          icon={FileUp}
          title="No documents yet"
          description="Upload a PDF, EPUB, or text file to get started"
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {uploads.map((upload) => (
            <UploadingDocumentCard
              key={upload.id}
              upload={upload}
              onDismiss={dismissUpload}
            />
          ))}
          {documents.map((doc) => (
            <DocumentCard
              key={doc.file_hash}
              document={doc}
              onDelete={(hash) => void removeDocument(hash)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
