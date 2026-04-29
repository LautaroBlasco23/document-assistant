import * as React from 'react'
import { client } from '../services'
import type { ProviderInfo, CredentialStatus } from '../types/api'

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
  const useProviders = (): UseProvidersResult => {
    const [providers, setProviders] = React.useState<ProviderInfo[]>([])
    const [loading, setLoading] = React.useState(true)

    React.useEffect(() => {
      client.listProviders()
        .then(setProviders)
        .catch(() => { /* ignore */ })
        .finally(() => setLoading(false))
    }, [])

    return { providers, loading }
  }

  const useCredentials = (): UseCredentialsResult => {
    const [credentials, setCredentials] = React.useState<CredentialStatus[]>([])
    const [loading, setLoading] = React.useState(true)

    const refresh = React.useCallback(() => {
      setLoading(true)
      client.listCredentials()
        .then(setCredentials)
        .catch(() => { /* ignore */ })
        .finally(() => setLoading(false))
    }, [])

    React.useEffect(() => {
      refresh()
    }, [refresh])

    return { credentials, loading, refresh }
  }

  const useSaveCredential = (): UseMutateResult<[string, string]> => {
    const [loading, setLoading] = React.useState(false)
    const [error, setError] = React.useState<string | null>(null)

    const execute = React.useCallback(async (provider: string, key: string) => {
      setLoading(true)
      setError(null)
      try {
        await client.saveCredential(provider, key)
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
