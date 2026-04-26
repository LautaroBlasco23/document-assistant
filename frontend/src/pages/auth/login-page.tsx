import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '@/auth/auth-context'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await login(email, password)
      navigate('/')
    } catch (err: any) {
      setError(err.message || 'Invalid credentials')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-100 dark:bg-surface">
      <div className="max-w-md w-full space-y-8 p-8 bg-surface dark:bg-surface-200 rounded-lg shadow">
        <div>
          <h2 className="text-2xl font-bold text-center text-gray-900 dark:text-slate-100">Sign in to Document Assistant</h2>
        </div>
        {error && (
          <div className="bg-danger-light dark:bg-danger/12 border border-danger/20 dark:border-danger/30 text-danger px-4 py-3 rounded">
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full rounded-md border border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 dark:text-slate-100 px-3 py-2 focus:border-primary focus:ring-primary"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full rounded-md border border-surface-200 dark:border-surface-200 bg-surface dark:bg-surface-200 dark:text-slate-100 px-3 py-2 focus:border-primary focus:ring-primary"
              required
            />
          </div>
          <button
            type="submit"
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary hover:bg-primary-hover focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
          >
            Sign in
          </button>
        </form>
        <div className="text-center text-sm text-gray-600 dark:text-slate-400">
          Don&apos;t have an account?{' '}
          <Link to="/register" className="text-primary hover:underline font-medium">
            Sign up
          </Link>
        </div>
      </div>
    </div>
  )
}
