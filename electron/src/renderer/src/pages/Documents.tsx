import { useState, useEffect, useRef } from 'react'
import { api } from '@/api/client'
import { useTask } from '@/hooks/useTask'

interface Document {
  file_hash: string
  filename: string
  num_chapters: number
}

export default function Documents() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [uploadingFile, setUploadingFile] = useState<string | null>(null)
  const [ingestTaskId, setIngestTaskId] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { task: ingestTask } = useTask(ingestTaskId)

  useEffect(() => {
    const loadDocuments = async () => {
      try {
        const response = await api.listDocuments()
        setDocuments(response.data)
      } catch (error) {
        console.error('Failed to load documents:', error)
      } finally {
        setLoading(false)
      }
    }

    loadDocuments()
  }, [])

  // Reload documents when ingest completes
  useEffect(() => {
    if (ingestTask?.status === 'completed') {
      const loadDocuments = async () => {
        const response = await api.listDocuments()
        setDocuments(response.data)
      }
      loadDocuments()
      setIngestTaskId(null)
    }
  }, [ingestTask?.status])

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setUploadingFile(file.name)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await api.ingestDocument(formData as any)
      setIngestTaskId(response.data.task_id)
    } catch (error) {
      console.error('Failed to upload file:', error)
      setUploadingFile(null)
    }

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleDeleteDocument = async (fileHash: string) => {
    if (window.confirm('Are you sure you want to delete this document?')) {
      try {
        await api.deleteDocument(fileHash)
        setDocuments(documents.filter((d) => d.file_hash !== fileHash))
      } catch (error) {
        console.error('Failed to delete document:', error)
      }
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Documents</h1>

      {/* Upload Section */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Upload Document</h2>
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.epub"
            onChange={handleFileSelect}
            className="hidden"
            id="file-input"
          />
          <label htmlFor="file-input" className="cursor-pointer">
            <div className="text-4xl mb-2">📄</div>
            <p className="text-gray-600 mb-2">
              {uploadingFile || 'Drag and drop or click to select a PDF or EPUB file'}
            </p>
            {ingestTask && (
              <div className="mt-4">
                <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all"
                    style={{
                      width: ingestTask.status === 'completed' ? '100%' : '75%',
                    }}
                  />
                </div>
                <p className="text-sm text-gray-600">
                  {ingestTask.status === 'running'
                    ? `Ingesting... ${ingestTask.progress}`
                    : 'Processing complete'}
                </p>
              </div>
            )}
          </label>
        </div>
      </div>

      {/* Documents List */}
      <div className="bg-white rounded-lg shadow">
        <h2 className="text-lg font-semibold text-gray-900 p-6 border-b">Documents</h2>
        {loading ? (
          <div className="p-6 text-center text-gray-600">Loading documents...</div>
        ) : documents.length === 0 ? (
          <div className="p-6 text-center text-gray-600">No documents yet</div>
        ) : (
          <div className="divide-y">
            {documents.map((doc) => (
              <div
                key={doc.file_hash}
                className="p-6 flex items-center justify-between hover:bg-gray-50"
              >
                <div className="flex-1">
                  <h3 className="font-medium text-gray-900">{doc.filename}</h3>
                  <p className="text-sm text-gray-600 mt-1">
                    {doc.num_chapters} chapters • {doc.file_hash.slice(0, 12)}
                  </p>
                </div>
                <button
                  onClick={() => handleDeleteDocument(doc.file_hash)}
                  className="text-red-600 hover:text-red-700 font-medium text-sm"
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
