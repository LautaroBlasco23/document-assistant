import { useEffect } from 'react'
import { RouterProvider } from 'react-router-dom'
import { router } from './router'
import { AuthProvider } from './auth/auth-context'
import { ErrorToasts } from './components/ui/error-toasts'
import { useTaskStore } from './stores/task-store'

function App() {
  useEffect(() => {
    useTaskStore.getState().rehydrateFromBackend()
  }, [])

  return (
    <AuthProvider>
      <RouterProvider router={router} />
      <ErrorToasts />
    </AuthProvider>
  )
}

export default App
