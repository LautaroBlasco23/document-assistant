import * as React from 'react'
import { client } from '../services'
import type { ProviderInfo, CredentialStatus } from '../types/api'
import { useRefDataStore } from '../stores/reference-data-store'

interface UseProvidersResult {
  providers: ProviderInfo[]
  loading: boolean
}

interface UseCredentialsResult {
  credentials: CredentialStatus[]
  loading: boolean
  refresh: () => void
}

interface UseMutateResult<TArgs extends unknown[] = []> {
  execute: (...args: TArgs) => Promise<void>
  loading: boolean
  error: string | null
}

interface UseProviderCredentialsResult {
  useProviders: () => UseProvidersResult
  useCredentials: () => UseCredentialsResult
  useSaveCredential: () => UseMutateResult<[string, string]>
  useDeleteCredential: () => UseMutateResult<[string]>
  useTestConnection: () => UseMutateResult<[string, string?]>
}

export function useProviderCredentials(): UseProviderCredentialsResult {
  // ─── Data hooks (read from shared store, trigger one-time fetch) ──────────

  const useProviders = (): UseProvidersResult => {
    React.useEffect(() => {
      void useRefDataStore.getState().loadCredentials()
    }, [])

    const providers = useRefDataStore((s) => s.providers)
    const loading = useRefDataStore((s) => s.credentialsLoading)
    return { providers, loading }
  }

  const useCredentials = (): UseCredentialsResult => {
    React.useEffect(() => {
      void useRefDataStore.getState().loadCredentials()
    }, [])

    const credentials = useRefDataStore((s) => s.credentials)
    const loading = useRefDataStore((s) => s.credentialsLoading)

    const refresh = React.useCallback(() => {
      useRefDataStore.setState({ credentialsLoaded: false })
      void useRefDataStore.getState().loadCredentials()
    }, [])

    return { credentials, loading, refresh }
  }

  // ─── Mutation hooks (still factory-local, fresh state per call) ───────────

  const useSaveCredential = (): UseMutateResult<[string, string]> => {
    const [loading, setLoading] = React.useState(false)
    const [error, setError] = React.useState<string | null>(null)

    const execute = React.useCallback(async (provider: string, key: string) => {
      setLoading(true)
      setError(null)
      try {
        await client.saveCredential(provider, key)
        // Invalidate credentials cache so next load fetches fresh
        useRefDataStore.setState({ credentialsLoaded: false })
      } catch (e) {
        setError(String(e))
      } finally {
        setLoading(false)
      }
    }, [])

    return { execute, loading, error }
  }

  const useDeleteCredential = (): UseMutateResult<[string]> => {
    const [loading, setLoading] = React.useState(false)
    const [error, setError] = React.useState<string | null>(null)

    const execute = React.useCallback(async (provider: string) => {
      setLoading(true)
      setError(null)
      try {
        await client.deleteCredential(provider)
        useRefDataStore.setState({ credentialsLoaded: false })
      } catch (e) {
        setError(String(e))
      } finally {
        setLoading(false)
      }
    }, [])

    return { execute, loading, error }
  }

  const useTestConnection = (): UseMutateResult<[string, string?]> => {
    const [loading, setLoading] = React.useState(false)
    const [error, setError] = React.useState<string | null>(null)

    const execute = React.useCallback(async (provider: string, apiKey?: string) => {
      setLoading(true)
      setError(null)
      try {
        await client.testConnection(provider, apiKey)
      } catch (e) {
        setError(String(e))
      } finally {
        setLoading(false)
      }
    }, [])

    return { execute, loading, error }
  }

  return {
    useProviders,
    useCredentials,
    useSaveCredential,
    useDeleteCredential,
    useTestConnection,
  }
}

export default useProviderCredentials
