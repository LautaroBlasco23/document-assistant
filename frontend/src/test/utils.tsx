import { render, type RenderOptions } from '@testing-library/react'
import { MemoryRouter, type MemoryRouterProps } from 'react-router-dom'
import { AuthProvider } from '@/auth/auth-context'
import userEvent from '@testing-library/user-event'
import { type ReactElement } from 'react'

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  routerProps?: MemoryRouterProps
}

export function renderWithProviders(
  ui: ReactElement,
  options: CustomRenderOptions = {}
) {
  const { routerProps, ...renderOptions } = options

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <MemoryRouter {...routerProps}>
        <AuthProvider>{children}</AuthProvider>
      </MemoryRouter>
    )
  }

  return {
    user: userEvent.setup(),
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
  }
}

// Re-export testing-library utilities so tests can import everything from here
export * from '@testing-library/react'
