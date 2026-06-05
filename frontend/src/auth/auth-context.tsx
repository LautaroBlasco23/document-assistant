import { createContext, useContext, useState, useEffect, useMemo, type ReactNode } from 'react'
import { client } from '../services'
import type { UserProfile } from '../types/api'

interface AuthContextType {
  user: UserProfile | null
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, displayName?: string) => Promise<void>
  logout: () => void
  refetchUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [token, setToken] = useState<string | null>(localStorage.getItem('auth_token'))
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (token) {
      fetchUser()
    } else {
      setIsLoading(false)
    }
  }, [token])

  const fetchUser = async () => {
    try {
      const data = await client.getMe()
      setUser(data)
    } catch {
      logout()
    } finally {
      setIsLoading(false)
    }
  }

  const login = async (email: string, password: string) => {
    const data = await client.login(email, password)
    setToken(data.access_token)
    localStorage.setItem('auth_token', data.access_token)
    await fetchUser()
  }

  const register = async (email: string, password: string, displayName?: string) => {
    const data = await client.register(email, password, displayName)
    setToken(data.access_token)
    localStorage.setItem('auth_token', data.access_token)
    await fetchUser()
  }

  const logout = () => {
    setUser(null)
    setToken(null)
    localStorage.removeItem('auth_token')
  }

  const refetchUser = async () => {
    const authToken = token || localStorage.getItem('auth_token')
    if (authToken) await fetchUser()
  }

  const value = useMemo(
    () => ({ user, token, isLoading, login, register, logout, refetchUser }),
    [user, token, isLoading, login, register, logout, refetchUser],
  )

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
