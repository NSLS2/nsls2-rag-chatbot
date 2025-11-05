import { useEffect, useState } from 'react'
import { listDocuments, deleteDocument, reindexDocument, AppDocument } from '../lib/api'
import { useAppStore } from '../store/useAppStore'

export default function DocumentsList() {
  const appId = useAppStore((s) => s.appId)
  const [docs, setDocs] = useState<AppDocument[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const { items } = await listDocuments(appId, 200)
      setDocs(items)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [appId])

  async function onDelete(id: number) {
    if (!confirm('Delete this document?')) return
    await deleteDocument(id)
    await load()
  }

  async function onReindex(id: number) {
    await reindexDocument(id)
    await load()
  }

  return (
    <div className="mt-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-medium">Uploaded files</h3>
        <button onClick={load} className="text-sm px-2 py-1 rounded border">Refresh</button>
      </div>
      {error && <div className="text-sm text-red-600 mb-2">{error}</div>}
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left border-b">
              <th className="py-2 pr-4">Filename</th>
              <th className="py-2 pr-4">Size</th>
              <th className="py-2 pr-4">Chunks</th>
              <th className="py-2 pr-4">Model</th>
              <th className="py-2 pr-4">Uploaded</th>
              <th className="py-2"></th>
            </tr>
          </thead>
          <tbody>
            {docs.map(d => (
              <tr key={d.id} className="border-b">
                <td className="py-2 pr-4">{d.filename}</td>
                <td className="py-2 pr-4">{d.size_bytes ? `${(d.size_bytes/1024/1024).toFixed(2)} MB` : '-'}</td>
                <td className="py-2 pr-4">{d.chunk_count ?? '-'}</td>
                <td className="py-2 pr-4">{d.model ?? '-'}</td>
                <td className="py-2 pr-4">{d.created_at ? new Date(d.created_at).toLocaleString() : '-'}</td>
                <td className="py-2">
                  <div className="flex gap-2">
                    <button onClick={()=>onReindex(d.id)} className="px-2 py-1 rounded bg-indigo-600 text-white">Reindex</button>
                    <button onClick={()=>onDelete(d.id)} className="px-2 py-1 rounded bg-red-600 text-white">Delete</button>
                  </div>
                </td>
              </tr>
            ))}
            {docs.length === 0 && !loading && (
              <tr>
                <td colSpan={6} className="py-4 text-center text-gray-500">No files yet</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
