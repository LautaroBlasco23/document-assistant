import { useEffect, useState } from 'react'

interface UserLimits {
  max_documents: number
  max_knowledge_trees: number
  current_documents: number
  current_knowledge_trees: number
  can_create_document: boolean
  can_create_tree: boolean
}

export function PlanPage() {
  const [limits, setLimits] = useState<UserLimits | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const token = localStorage.getItem('auth_token')
    fetch('/api/users/me/limits', {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(async (res) => {
        if (!res.ok) throw new Error('Failed to load limits')
        return res.json()
      })
      .then((data) => {
        setLimits(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/3"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  if (error || !limits) {
    return (
      <div className="p-6">
        <div className="text-red-600">{error || 'Failed to load limits'}</div>
      </div>
    )
  }

  const treePercent = Math.min((limits.current_knowledge_trees / limits.max_knowledge_trees) * 100, 100)
  const docPercent = Math.min((limits.current_documents / limits.max_documents) * 100, 100)

  return (
    <div className="p-6 max-w-2xl">
      <h2 className="text-2xl font-bold mb-6">Your Plan</h2>

      <div className="space-y-6">
        {/* Knowledge Trees */}
        <div className="bg-white border rounded-lg p-5">
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-semibold text-gray-900">Knowledge Trees</h3>
            <span className="text-sm font-medium text-gray-600">
              {limits.current_knowledge_trees} / {limits.max_knowledge_trees}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2.5 mb-3">
            <div
              className={`h-2.5 rounded-full transition-all ${
                treePercent >= 90 ? 'bg-red-500' : 'bg-blue-600'
              }`}
              style={{ width: `${treePercent}%` }}
            />
          </div>
          {!limits.can_create_tree && (
            <p className="text-sm text-red-600">
              You've reached your knowledge tree limit. Delete some trees or contact admin to upgrade.
            </p>
          )}
        </div>

        {/* Documents */}
        <div className="bg-white border rounded-lg p-5">
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-semibold text-gray-900">Documents</h3>
            <span className="text-sm font-medium text-gray-600">
              {limits.current_documents} / {limits.max_documents}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2.5 mb-3">
            <div
              className={`h-2.5 rounded-full transition-all ${
                docPercent >= 90 ? 'bg-red-500' : 'bg-green-600'
              }`}
              style={{ width: `${docPercent}%` }}
            />
          </div>
          {!limits.can_create_document && (
            <p className="text-sm text-red-600">
              You've reached your document limit. Delete some documents or contact admin to upgrade.
            </p>
          )}
        </div>

        {/* Plan Info */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="font-medium text-blue-900 mb-2">Free Plan</h4>
          <p className="text-sm text-blue-700">
            You're on the Free plan with {limits.max_knowledge_trees} knowledge trees and {limits.max_documents} documents.
            Contact your admin to upgrade to a higher plan.
          </p>
        </div>
      </div>
    </div>
  )
}
