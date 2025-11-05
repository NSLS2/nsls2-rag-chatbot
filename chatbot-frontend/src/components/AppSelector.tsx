import { useEffect, useState } from 'react'
import { fetchAppIds } from '../lib/api'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '../store/useAppStore'

export default function AppSelector() {
  const appId = useAppStore((s) => s.appId)
  const setAppId = useAppStore((s) => s.setAppId)
  const navigate = useNavigate()
  const [list, setList] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const ids = await fetchAppIds()
      setList(ids)
      // Preserve current selection if it's not in list
    } catch (e: any) {
      setError(e?.message || 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])


  return (
    <div className="flex items-center gap-2">
      <label className="text-sm">App ID</label>
      <select
        className="border rounded px-2 py-1 min-w-[12rem]"
        value={list.includes(appId) ? appId : ''}
        onChange={(e)=>{
          const v = e.target.value
          if (v === '__custom__') return
          setAppId(v)
          navigate(`/app/${encodeURIComponent(v)}`)
        }}
      >
        <option value="" disabled>{loading ? 'Loading…' : (list.length ? 'Select an app' : 'No apps found')}</option>
        {list.map(id => (
          <option key={id} value={id}>{id}</option>
        ))}
      </select>
      <button onClick={load} className="text-xs px-2 py-1 rounded border">Refresh</button>
      {error && <span className="text-xs text-red-600">{error}</span>}
    </div>
  )
}
