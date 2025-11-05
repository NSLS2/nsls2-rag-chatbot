import { useState } from 'react'
import { search } from '../lib/api'
import { useAppStore } from '../store/useAppStore'
import AppSelector from './AppSelector'

export default function SearchPanel() {
  const [query, setQuery] = useState('What is RAG?')
  const [results, setResults] = useState<any[]>([])
  const appId = useAppStore((s) => s.appId)
  const busy = useAppStore((s) => s.busy)
  const setBusy = useAppStore((s) => s.setBusy)
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})

  async function onSearch() {
    if (!query.trim()) return
    setBusy(true)
    setResults([])
    try {
      const res = await search(query, 5, appId)
      setResults(res.results || [])
    } catch (e: any) {
      setResults([{ id: 'error', score: 0, payload: { text: e?.response?.data?.detail || e.message } }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      <AppSelector />
      <div className="flex gap-2">
        <input className="flex-1 border rounded px-3 py-2" value={query} onChange={(e)=>setQuery(e.target.value)} />
        <button disabled={busy} onClick={onSearch} className="px-3 py-2 rounded bg-indigo-600 text-white disabled:opacity-50">Search</button>
      </div>
      <div className="rounded border bg-white p-3">
        <div className="font-medium mb-2">Results</div>
        <ul className="space-y-2">
          {results.map((r,i)=>{
            const full = (r?.payload?.text || '')
            const isOpen = !!expanded[i]
            const display = isOpen ? full : full.slice(0,200)
            return (
              <li key={i} className="text-sm">
                <span className="text-gray-500">[{r.score?.toFixed?.(3)}]</span>{' '}
                <span className="whitespace-pre-wrap">{display}</span>
                {full.length > 200 && (
                  <button
                    className="ml-2 text-indigo-600 hover:underline text-xs"
                    onClick={()=> setExpanded((e)=> ({...e, [i]: !isOpen}))}
                  >{isOpen ? 'Show less' : 'Show more'}</button>
                )}
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}
