import { useEffect, useState, useMemo } from 'react'
import { ChatTurn, fetchHistory } from '../lib/api'
import { useAppStore } from '../store/useAppStore'
import { useChatStore, defaultChatState } from '../store/useChatStore'

export default function ChatMessages({ refreshKey }: { refreshKey?: number }) {
  const appId = useAppStore((s) => s.appId)
  const [items, setItems] = useState<ChatTurn[]>([])
  const [loading, setLoading] = useState(false)
  const chatState = useChatStore((s) => s.byApp[appId] || defaultChatState)

  async function load() {
    if (!appId) return
    setLoading(true)
    try {
      const data = await fetchHistory(appId, 200)
      // API returns newest first; render oldest first
      setItems(data.slice().reverse())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appId, refreshKey])

  if (!appId) return null

  // Determine latest turn id so we can suppress premature rating display while awaiting feedback
  const latestTurnId = useMemo(() => (items.length ? items[items.length - 1].id : null), [items])

  return (
    <div className="space-y-3">
      {loading && <div className="text-xs text-gray-500">Loading history…</div>}
      {items.map((t) => (
        <div key={t.id} className="space-y-2">
          <div className="flex">
            <div className="ml-auto max-w-[80%] rounded-lg bg-green-50 border border-green-200 px-3 py-2 text-sm">
              <div className="text-xs text-gray-400 mb-1">You</div>
              <div className="whitespace-pre-wrap">{t.user_message}</div>
            </div>
          </div>
          <div className="flex">
            <div className="mr-auto max-w-[80%] rounded-lg bg-white border px-3 py-2 text-sm">
              <div className="text-xs text-gray-400 mb-1">Assistant</div>
              <div className="whitespace-pre-wrap">{t.assistant_answer}</div>
              {/* Show rating summary ONLY if rating exists AND (not the latest awaiting-feedback turn) */}
              {typeof (t as any).rating === 'number' && (t as any).rating != null && (!chatState.awaitingFeedback || t.id !== latestTurnId) && (
                <div className="mt-1 text-xs text-gray-600">Rated: <span className="font-semibold">{(t as any).rating}/5</span>{(t as any).comment ? ` — ${(t as any).comment}` : ''}</div>
              )}
              {/* Sources (documents) */}
              {Array.isArray(t.sources) && t.sources.length > 0 && (
                <details className="mt-3 group">
                  <summary className="cursor-pointer select-none text-xs text-indigo-600 font-medium flex items-center gap-1">
                    <span>View retrieved documents ({t.sources.length})</span>
                  </summary>
                  <div className="mt-2 space-y-2">
                    {t.sources.map((s: any, idx: number) => {
                      const text = (s?.payload?.text || '').trim()
                      return (
                        <div key={idx} className="rounded border bg-gray-50 p-2 text-xs">
                          <div className="mb-1 flex justify-between">
                            <span className="font-semibold">Doc {idx + 1}</span>
                            {typeof s.score === 'number' && (
                              <span className="text-gray-500">score {(s.score as number).toFixed(4)}</span>
                            )}
                          </div>
                          <div className="whitespace-pre-wrap max-h-40 overflow-auto leading-relaxed">
                            {text || <span className="italic text-gray-400">(no text payload)</span>}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </details>
              )}
            </div>
          </div>
        </div>
      ))}
      {/* If user typed a message that hasn't persisted yet (input cleared on send), nothing extra to show here. */}
      {!loading && items.length === 0 && (
        <div className="text-sm text-gray-500">No history yet. Ask your first question!</div>
      )}
    </div>
  )
}
