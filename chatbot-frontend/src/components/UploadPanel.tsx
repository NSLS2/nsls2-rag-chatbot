import { useState } from 'react'
import { uploadFile } from '../lib/api'
import { useAppStore } from '../store/useAppStore'
import AppSelector from './AppSelector'
import DocumentsList from './DocumentsList'

export default function UploadPanel() {
  const [file, setFile] = useState<File | null>(null)
  const [chunk, setChunk] = useState(800)
  const [msg, setMsg] = useState('')
  const appId = useAppStore((s) => s.appId)
  const busy = useAppStore((s) => s.busy)
  const setBusy = useAppStore((s) => s.setBusy)

  async function onUpload() {
    if (!file) return
    setMsg('')
    setBusy(true)
    try {
      const res = await uploadFile(file, appId, chunk)
      setMsg(`Uploaded: ${res.chunks} chunks -> ${res.collection}`)
    } catch (e: any) {
      setMsg(e?.response?.data?.detail || e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      <AppSelector />
      <div className="flex items-center gap-3">
        <input type="file" onChange={(e)=>setFile(e.target.files?.[0] ?? null)} />
        <label className="text-sm">Chunk size</label>
        <input type="number" className="border rounded px-2 py-1 w-24" value={chunk} onChange={(e)=>setChunk(parseInt(e.target.value||'800'))} />
        <button disabled={!file || busy} onClick={onUpload} className="px-3 py-1 rounded bg-blue-600 text-white disabled:opacity-50">Upload</button>
      </div>
      {msg && <div className="text-sm text-gray-700">{msg}</div>}
      <DocumentsList />
    </div>
  )
}
