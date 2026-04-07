import { useEffect } from 'react'
import { RouterProvider } from 'react-router-dom'
import { router } from './router'
import { ErrorToasts } from './components/ui/error-toasts'
import { useTaskStore } from './stores/task-store'

function App() {
  useEffect(() => {
    useTaskStore.getState().rehydrateFromBackend()
  }, [])

  return (
    <>
      <RouterProvider router={router} />
      <ErrorToasts />
    </>
  )
}

export default App
