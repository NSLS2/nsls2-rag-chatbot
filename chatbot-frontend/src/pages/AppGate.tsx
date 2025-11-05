import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchAppIds, createOrUpdateApp } from '../lib/api'
import { useAppStore } from '../store/useAppStore'

export default function AppGate() {
  const navigate = useNavigate()
  const setAppId = useAppStore((s) => s.setAppId)
  const setAppIds = useAppStore((s) => s.setAppIds)
  const [list, setList] = useState<string[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [newId, setNewId] = useState<string>('')

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const ids = await fetchAppIds()
      setList(ids)
      setAppIds(ids)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  function onSelectChange(v: string) {
    setSelectedId(v)
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="w-full max-w-md bg-white rounded shadow p-6 space-y-6">
        <div className="flex items-center gap-2">
          <button
            aria-label="Back"
            className="inline-flex items-center justify-center w-8 h-8 rounded hover:bg-gray-100 text-gray-700"
            onClick={() => navigate(-1)}
            title="Back"
          >
            <span aria-hidden className="text-lg">←</span>
          </button>
          <h1 className="text-xl font-semibold">Choose or create an App</h1>
        </div>
        <div className="space-y-2">
          <label className="text-sm">Select an app</label>
          <select
            className="w-full border rounded px-3 py-2"
            value={selectedId}
            onChange={(e)=> onSelectChange(e.target.value)}
          >
            <option value="" disabled>{loading ? 'Loading…' : (list.length ? 'Select app' : 'No apps found')}</option>
            {list.map(id => (<option key={id} value={id}>{id}</option>))}
          </select>
        </div>
        <div className="space-y-2">
          <label className="text-sm">Or create new</label>
          <div className="flex gap-2">
            <input className="flex-1 border rounded px-3 py-2" placeholder="Enter new app id" value={newId} onChange={(e)=> setNewId(e.target.value)} />
            <button
              onClick={async () => {
                if (!newId.trim()) return
                setSaving(true)
                setError(null)
                try {
                  await createOrUpdateApp(newId)
                  await load()
                  setSelectedId(newId)
                  setAppId(newId)
                  setNewId('')
                } catch (e: any) {
                  setError(e?.response?.data?.detail || e.message)
                } finally {
                  setSaving(false)
                }
              }}
              disabled={!newId.trim() || saving}
              className="px-3 py-2 rounded bg-green-600 text-white disabled:opacity-50"
            >Create</button>
          </div>
        </div>
        {error && <div className="text-sm text-red-600">{error}</div>}
        <div className="pt-2 space-y-2">
          <button
            disabled={!selectedId.trim()}
            onClick={() => { setAppId(selectedId); navigate(`/app/${encodeURIComponent(selectedId)}`) }}
            className="w-full px-3 py-2 rounded bg-indigo-600 text-white disabled:opacity-50"
          >Continue</button>
        </div>
      </div>
    </div>
  )
}
