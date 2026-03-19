import { useState, useEffect } from 'react'
import { api } from '@/api/client'
import { useTask } from '@/hooks/useTask'

interface Document {
  file_hash: string
  filename: string
  num_chapters: number
}

interface TaskResult {
  chapter: number
  summary?: string
  qa_pairs?: Array<{ question: string; answer: string }>
  flashcards?: Array<{ question: string; answer: string }>
}

export default function ChapterAnalysis() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [selectedDoc, setSelectedDoc] = useState<string>('')
  const [selectedChapter, setSelectedChapter] = useState(1)
  const [taskType, setTaskType] = useState<'summarize' | 'qa' | 'flashcards' | null>(null)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [result, setResult] = useState<TaskResult | null>(null)

  const { task } = useTask(taskId, (res) => {
    if (res.summary) {
      setResult({ chapter: res.chapter, summary: String(res.summary) })
    } else if (res.qa_pairs) {
      setResult({ chapter: res.chapter, qa_pairs: res.qa_pairs as any })
    } else if (res.flashcards) {
      setResult({ chapter: res.chapter, flashcards: res.flashcards as any })
    }
  })

  useEffect(() => {
    const loadDocuments = async () => {
      try {
        const response = await api.listDocuments()
        setDocuments(response.data)
        if (response.data.length > 0) {
          setSelectedDoc(response.data[0].file_hash)
        }
      } catch (error) {
        console.error('Failed to load documents:', error)
      }
    }

    loadDocuments()
  }, [])

  const currentDoc = documents.find((d) => d.file_hash === selectedDoc)
  const maxChapter = currentDoc?.num_chapters || 0

  const handleStartTask = async (type: 'summarize' | 'qa' | 'flashcards') => {
    if (!selectedDoc) return

    setTaskType(type)
    setResult(null)

    try {
      const bookTitle = currentDoc?.filename || 'Unknown'
      let response

      switch (type) {
        case 'summarize':
          response = await api.summarizeChapter(selectedChapter, bookTitle)
          break
        case 'qa':
          response = await api.generateQA(selectedChapter, bookTitle)
          break
        case 'flashcards':
          response = await api.generateFlashcards(selectedChapter, bookTitle)
          break
      }

      setTaskId(response.data.task_id)
    } catch (error) {
      console.error('Failed to start task:', error)
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Chapter Analysis</h1>

      {/* Settings */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Settings</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Document</label>
            <select
              value={selectedDoc}
              onChange={(e) => setSelectedDoc(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {documents.map((doc) => (
                <option key={doc.file_hash} value={doc.file_hash}>
                  {doc.filename}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Chapter</label>
            <input
              type="number"
              min={1}
              max={maxChapter}
              value={selectedChapter}
              onChange={(e) => setSelectedChapter(Math.max(1, parseInt(e.target.value) || 1))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <button
          onClick={() => handleStartTask('summarize')}
          disabled={!selectedDoc || task?.status === 'running'}
          className="px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 transition-colors font-medium"
        >
          📝 Summarize
        </button>
        <button
          onClick={() => handleStartTask('qa')}
          disabled={!selectedDoc || task?.status === 'running'}
          className="px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors font-medium"
        >
          ❓ Q&A
        </button>
        <button
          onClick={() => handleStartTask('flashcards')}
          disabled={!selectedDoc || task?.status === 'running'}
          className="px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 transition-colors font-medium"
        >
          🎴 Flashcards
        </button>
      </div>

      {/* Progress */}
      {task && task.status === 'running' && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <p className="text-blue-900 font-medium mb-2">Processing...</p>
          <p className="text-sm text-blue-700">{task.progress}</p>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            {taskType === 'summarize' && 'Summary'}
            {taskType === 'qa' && 'Q&A Pairs'}
            {taskType === 'flashcards' && 'Flashcards'}
          </h2>

          {taskType === 'summarize' && result.summary && (
            <div className="prose prose-sm max-w-none">
              <p className="text-gray-800 leading-relaxed">{result.summary}</p>
            </div>
          )}

          {(taskType === 'qa' || taskType === 'flashcards') && result.qa_pairs && (
            <div className="space-y-4">
              {result.qa_pairs.map((pair, idx) => (
                <div key={idx} className="border border-gray-200 rounded-lg p-4">
                  <p className="font-medium text-gray-900 mb-2">{pair.question}</p>
                  <p className="text-gray-700">{pair.answer}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
