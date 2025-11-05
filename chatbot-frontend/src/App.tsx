import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import UploadPanel from './components/UploadPanel'
import ChatPanel from './components/ChatPanel'
import SearchPanel from './components/SearchPanel'
import AnalyticsPanel from './components/AnalyticsPanel'
import AppGate from './pages/AppGate'
import { useAppStore } from './store/useAppStore'
import { fetchApp } from './lib/api'

export default function App() {
  const [tab, setTab] = useState<'chat' | 'upload' | 'search' | 'analytics'>('chat')
  const params = useParams()
  const appId = (params.appId as string) || useAppStore((s) => s.appId)
  const setAppId = useAppStore((s) => s.setAppId)
  const [displayName, setDisplayName] = useState<string | undefined>(undefined)
  const navigate = useNavigate()

  useEffect(() => {
    if (!appId?.trim()) {
      setDisplayName(undefined)
    }
  }, [appId])

  useEffect(() => {
    // Sync route param to store so components relying on store continue to work
    if (appId && useAppStore.getState().appId !== appId) {
      setAppId(appId)
    }
  }, [appId, setAppId])

  useEffect(() => {
    let cancelled = false
    async function load() {
      if (!appId?.trim()) return
      try {
        const { app } = await fetchApp(appId)
        if (!cancelled) setDisplayName(app.display_name)
      } catch {
        if (!cancelled) setDisplayName(undefined)
      }
    }
    load()
    return () => { cancelled = true }
  }, [appId])

  // No gate here; routing handles it.
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="border-b bg-white">
        <div className="mx-auto max-w-5xl px-4 h-14 flex items-center gap-6">
          {/* Left: Back + Title */}
          <div className="flex items-center gap-2 min-w-0">
            <button
              aria-label="Back"
              className="inline-flex items-center justify-center w-9 h-9 rounded hover:bg-gray-100 text-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-gray-400"
              onClick={() => navigate('/select')}
              title="Back"
            >
              <span aria-hidden className="text-lg">←</span>
            </button>
            <h1
              className="text-lg font-semibold tracking-tight truncate max-w-[34ch]"
              title={displayName ? `${displayName} (${appId})` : `RAG Chatbot (${appId})`}
            >
              {displayName ? `${displayName} (${appId})` : `RAG Chatbot (${appId})`}
            </h1>
          </div>
          {/* Tabs: aligned horizontally to the right of title */}
          <nav className="flex items-center gap-2 ml-auto" aria-label="Primary sections">
            {(['chat','upload','search','analytics'] as const).map(key => (
              <button
                key={key}
                aria-current={tab===key? 'page': undefined}
                onClick={()=>setTab(key)}
                className={`px-3 h-9 inline-flex items-center rounded text-sm font-medium transition-colors border border-transparent focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-gray-400
                  ${tab===key ? 'bg-gray-900 text-white shadow-sm' : 'bg-gray-200 hover:bg-gray-300 text-gray-800'}`}
              >
                {key.charAt(0).toUpperCase()+key.slice(1)}
              </button>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        {tab === 'chat' && <ChatPanel />}
        {tab === 'upload' && <UploadPanel />}
  {tab === 'search' && <SearchPanel />}
  {tab === 'analytics' && <AnalyticsPanel />}
      </main>
    </div>
  )
}
