import { useEffect } from 'react'
import { RouterProvider } from 'react-router-dom'
import { router } from './router'
import { ErrorToasts } from './components/ui/error-toasts'
import { useUploadStore } from './stores/upload-store'
import { useTaskStore } from './stores/task-store'

function App() {
  useEffect(() => {
    useUploadStore.getState().rehydrate()
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
