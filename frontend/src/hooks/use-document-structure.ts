import { useEffect, useState } from 'react'
import { useDocumentStore } from '../stores/document-store'
import type { DocumentStructureOut } from '../types/api'

export function useDocumentStructure(hash: string): {
  structure: DocumentStructureOut | null
  loading: boolean
} {
  const structureCache = useDocumentStore((state) => state.structureCache)
  const fetchStructure = useDocumentStore((state) => state.fetchStructure)
  const [loading, setLoading] = useState(false)

  const structure = structureCache[hash] ?? null

  useEffect(() => {
    if (structureCache[hash]) return

    setLoading(true)
    void fetchStructure(hash).finally(() => setLoading(false))
  }, [hash, structureCache, fetchStructure])

  return { structure, loading }
}
