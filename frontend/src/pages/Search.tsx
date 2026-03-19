import { useState } from 'react'
import { api } from '@/api/client'

interface Chunk {
  id: string
  text: string
  chapter: number
  page?: number
  score?: number
}

export default function Search() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Chunk[]>([])
  const [loading, setLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setLoading(true)
    setHasSearched(true)

    try {
      const response = await api.search(query, 20)
      setResults(response.data.chunks)
    } catch (error) {
      console.error('Search failed:', error)
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Search</h1>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="mb-6">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search across all documents..."
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
      </form>

      {/* Results */}
      {hasSearched && (
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b">
            <h2 className="text-lg font-semibold text-gray-900">
              Results {results.length > 0 && `(${results.length})`}
            </h2>
          </div>
          {loading ? (
            <div className="p-6 text-center text-gray-600">Searching...</div>
          ) : results.length === 0 ? (
            <div className="p-6 text-center text-gray-600">
              {query ? 'No results found' : 'Enter a search query'}
            </div>
          ) : (
            <div className="divide-y">
              {results.map((chunk) => (
                <div key={chunk.id} className="p-6 hover:bg-gray-50">
                  <div className="flex items-start justify-between mb-2">
                    <p className="text-sm text-gray-600">
                      Chapter {chunk.chapter}
                      {chunk.page && ` • Page ${chunk.page}`}
                    </p>
                    {chunk.score && (
                      <span className="text-sm font-medium text-blue-600">
                        {(chunk.score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                  <p className="text-gray-900 leading-relaxed">{chunk.text}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
