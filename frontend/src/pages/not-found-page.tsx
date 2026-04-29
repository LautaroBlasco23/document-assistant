import { useNavigate } from 'react-router-dom'
import { FileQuestion } from 'lucide-react'
import { Button } from '../components/ui/button'

export function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-center p-6">
      <FileQuestion className="h-16 w-16 text-text-tertiary" />
      <h1 className="text-2xl font-semibold text-text-secondary">Page not found</h1>
      <p className="text-text-tertiary">The page you're looking for doesn't exist.</p>
      <Button variant="secondary" onClick={() => navigate('/')}>
        Back to Library
      </Button>
    </div>
  )
}
