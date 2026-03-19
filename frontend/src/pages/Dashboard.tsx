import { useState, useEffect } from 'react'
import { useAppStore } from '@/stores/appStore'
import { api } from '@/api/client'
import { Link } from 'react-router-dom'

interface Document {
  file_hash: string
  filename: string
  num_chapters: number
}

export default function Dashboard() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const serviceHealth = useAppStore((state) => state.serviceHealth)

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

  const totalChapters = documents.reduce((sum, doc) => sum + doc.num_chapters, 0)
  const servicesHealthy = serviceHealth?.services.filter((s) => s.healthy).length || 0
  const totalServices = serviceHealth?.services.length || 0

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Dashboard</h1>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600 text-sm font-medium mb-2">Documents</p>
          <p className="text-3xl font-bold text-gray-900">{documents.length}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600 text-sm font-medium mb-2">Total Chapters</p>
          <p className="text-3xl font-bold text-gray-900">{totalChapters}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600 text-sm font-medium mb-2">Services</p>
          <p className="text-3xl font-bold text-gray-900">
            {servicesHealthy}/{totalServices}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600 text-sm font-medium mb-2">Status</p>
          <p className="text-2xl font-bold">
            {serviceHealth?.status === 'healthy' ? '✅ Healthy' : '⚠️ Degraded'}
          </p>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <Link
          to="/documents"
          className="bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
        >
          <div className="text-3xl mb-2">📄</div>
          <h3 className="font-semibold mb-1">Upload Documents</h3>
          <p className="text-sm opacity-90">Add PDF or EPUB files</p>
        </Link>
        <Link
          to="/search"
          className="bg-gradient-to-br from-green-500 to-green-600 text-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
        >
          <div className="text-3xl mb-2">🔍</div>
          <h3 className="font-semibold mb-1">Search</h3>
          <p className="text-sm opacity-90">Find content across documents</p>
        </Link>
        <Link
          to="/ask"
          className="bg-gradient-to-br from-purple-500 to-purple-600 text-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
        >
          <div className="text-3xl mb-2">❓</div>
          <h3 className="font-semibold mb-1">Ask Question</h3>
          <p className="text-sm opacity-90">Get answers using RAG</p>
        </Link>
      </div>

      {/* Recent Documents */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b">
          <h2 className="text-lg font-semibold text-gray-900">Recent Documents</h2>
        </div>
        {loading ? (
          <div className="p-6 text-center text-gray-600">Loading...</div>
        ) : documents.length === 0 ? (
          <div className="p-6 text-center text-gray-600">
            No documents yet.{' '}
            <Link to="/documents" className="text-blue-600 hover:text-blue-700 font-medium">
              Upload one now
            </Link>
          </div>
        ) : (
          <div className="divide-y">
            {documents.slice(0, 5).map((doc) => (
              <div key={doc.file_hash} className="p-6 hover:bg-gray-50">
                <h3 className="font-medium text-gray-900">{doc.filename}</h3>
                <p className="text-sm text-gray-600 mt-1">{doc.num_chapters} chapters</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
