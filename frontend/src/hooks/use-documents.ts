import { useEffect } from 'react'
import { useDocumentStore } from '../stores/document-store'
import type { DocumentOut } from '../types/api'

export function useDocuments(): { documents: DocumentOut[]; loading: boolean } {
  const documents = useDocumentStore((state) => state.documents)
  const loading = useDocumentStore((state) => state.loading)
  const fetchDocuments = useDocumentStore((state) => state.fetchDocuments)

  useEffect(() => {
    if (documents.length === 0) {
      void fetchDocuments()
    }
  }, [documents.length, fetchDocuments])

  return { documents, loading }
}
