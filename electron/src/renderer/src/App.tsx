import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from '@/components/Layout'
import Dashboard from '@/pages/Dashboard'
import Documents from '@/pages/Documents'
import Search from '@/pages/Search'
import AskQuestion from '@/pages/AskQuestion'
import ChapterAnalysis from '@/pages/ChapterAnalysis'
import Settings from '@/pages/Settings'

function App(): JSX.Element {
  const [isReady, setIsReady] = useState(false)

  useEffect(() => {
    // Check if API is available
    const checkHealth = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/health')
        if (response.ok) {
          setIsReady(true)
        }
      } catch (error) {
        console.error('Health check failed:', error)
        setTimeout(checkHealth, 1000)
      }
    }

    checkHealth()
  }, [])

  if (!isReady) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-800 mb-4">Document Assistant</h1>
          <p className="text-gray-600">Starting services...</p>
        </div>
      </div>
    )
  }

  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/search" element={<Search />} />
          <Route path="/ask" element={<AskQuestion />} />
          <Route path="/analysis" element={<ChapterAnalysis />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
