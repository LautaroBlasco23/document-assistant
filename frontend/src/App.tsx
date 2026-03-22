import { RouterProvider } from 'react-router-dom'
import { router } from './router'
import { ErrorToasts } from './components/ui/error-toasts'

function App() {
  return (
    <>
      <RouterProvider router={router} />
      <ErrorToasts />
    </>
  )
}

export default App
