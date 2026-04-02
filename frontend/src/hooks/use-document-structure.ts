import { useEffect, useState, useCallback } from 'react'
import { useDocumentStore } from '../stores/document-store'
import { client } from '../services'
import type { DocumentStructureOut } from '../types/api'

export function useDocumentStructure(hash: string): {
  structure: DocumentStructureOut | null
  loading: boolean
  refresh: () => Promise<void>
} {
  const structureCache = useDocumentStore((state) => state.structureCache)
  const setStructureCache = useDocumentStore((state) => state.setStructureCache)
  const fetchStructure = useDocumentStore((state) => state.fetchStructure)
  const [loading, setLoading] = useState(false)

  const structure = structureCache[hash] ?? null

  useEffect(() => {
    if (structureCache[hash]) return

    setLoading(true)
    void fetchStructure(hash).finally(() => setLoading(false))
  }, [hash, structureCache, fetchStructure])

  const refresh = useCallback(async () => {
    if (!hash) return
    setLoading(true)
    try {
      const structure = await client.documentStructure(hash)
      setStructureCache(hash, structure)
    } finally {
      setLoading(false)
    }
  }, [hash, setStructureCache])

  return { structure, loading, refresh }
}
