import { useRef, useState } from 'react'
import { chat, chatStream, submitFeedback } from '../lib/api'
import { useAppStore } from '../store/useAppStore'
import { useChatStore, defaultChatState } from '../store/useChatStore'
import AppSelector from './AppSelector'
import ChatMessages from './ChatMessages'
import { clearHistory } from '../lib/api'

export default function ChatPanel() {
  const appId = useAppStore((s) => s.appId)
  const busy = useAppStore((s) => s.busy)
  const setBusy = useAppStore((s) => s.setBusy)
  const chatState = useChatStore((s) => s.byApp[appId] || defaultChatState)
  const setChatState = useChatStore((s) => s.setStateFor)
  const resetChatState = useChatStore((s) => s.resetStateFor)
  const [typing, setTyping] = useState(false)
  const lastSentRef = useRef<string>('')
  const [refreshKey, setRefreshKey] = useState(0) as any

  async function onSend() {
    const msg = (chatState.lastMessage || '').trim()
    if (!msg) return
    if (chatState.awaitingFeedback) return
    setBusy(true)
    setTyping(true)
    // Preserve sent message for feedback, clear input immediately
    lastSentRef.current = msg
    setChatState(appId, { lastMessage: '', answer: '', sources: [], rating: null, comment: '' })
    // Progressive streaming accumulation
    let streamedAnswer = ''
    const mergeToken = (current: string, token: string) => {
      if (!current) return token
      // Improved heuristic:
      // 1. If current ends with a hyphen (word wrap), just concatenate.
      // 2. If current ends with an alphanumeric and token starts with a lowercase letter and token length < 6 (often subword) -> concatenate without space.
      // 3. Only insert space if last char isn't whitespace and token doesn't start with whitespace or punctuation and isn't a word-continuation.
      const last = current[current.length - 1]
      const isContinuation = /[A-Za-z0-9]$/.test(last) && /^[a-z]{1,6}\b/.test(token)
      if (last === '-') return current + token
      if (!/\s/.test(last) && token && !/^[\s.,;:!?')\]]/.test(token) && !isContinuation) {
        return current + ' ' + token
      }
      return current + token
    }
    try {
      const { answer, sources } = await chatStream({
        message: msg,
        app_id: appId,
        top_k: 5,
        onToken: (t) => {
          streamedAnswer = mergeToken(streamedAnswer, t)
          setChatState(appId, { answer: streamedAnswer })
        }
      })
      // Final answer override (ensures exact final text) + sources + mark for feedback
      setChatState(appId, { answer: answer || streamedAnswer, sources: sources || [], awaitingFeedback: true })
      setRefreshKey((k: number) => k + 1)
    } catch (e: any) {
      setChatState(appId, { answer: e?.response?.data?.detail || e.message })
    } finally {
      setBusy(false)
      setTyping(false)
    }
  }

  async function onSubmitFeedback() {
    if (!chatState.awaitingFeedback || chatState.rating == null) return
    setBusy(true)
    try {
      await submitFeedback({
        app_id: appId,
        query: lastSentRef.current,
        response: chatState.answer,
        rating: chatState.rating,
        comment: chatState.comment || undefined,
        sources: chatState.sources,
      })
      // Re-enable input and refresh history so the rating appears under the persisted turn
      setChatState(appId, { awaitingFeedback: false, comment: '', rating: null })
      setRefreshKey((k: number) => k + 1)
    } catch (e: any) {
      // Surface error inline
      alert(e?.response?.data?.detail || e.message)
    } finally {
      setBusy(false)
    }
  }

  async function onClearHistory() {
    if (!appId) return
    if (!confirm('Clear all chat history for this app?')) return
    try {
      await clearHistory(appId)
      // also reset local chat state so UI is clean
      resetChatState(appId)
      setRefreshKey((k: number) => k + 1)
    } catch (e: any) {
      alert(e?.response?.data?.detail || e.message)
    }
  }

  // Clear feedback action was removed from Chat page to keep it focused; it's available in Analytics

  return (
    <div className="flex flex-col gap-4 h-full">
      <div className="flex items-center gap-2">
        <div className="flex-1"><AppSelector /></div>
      </div>

      <div className="flex items-center justify-between text-sm text-gray-700">
        <div className="font-medium">Chat history</div>
        <button
          onClick={onClearHistory}
          className="inline-flex items-center gap-1 px-2 py-1 rounded border text-red-600 border-red-600 hover:bg-red-50"
          aria-label="Clear chat history"
          title="Clear chat history"
        >
          <svg aria-hidden width="14" height="14" viewBox="0 0 24 24" fill="currentColor" className="text-red-600">
            <path d="M9 3h6a1 1 0 0 1 1 1v1h5v2h-1l-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 7H3V5h5V4a1 1 0 0 1 1-1Zm2 3h2V5h-2v1ZM7 9l1 12h8l1-12H7Z"/>
          </svg>
          <span>Clear chat</span>
        </button>
      </div>

      <div className="flex-1 overflow-auto border rounded p-3 bg-gray-50 space-y-3">
        <ChatMessages refreshKey={refreshKey} />
        {/* Optimistic user bubble for the just-sent message while awaiting response */}
        {typing && lastSentRef.current && (
          <div className="flex">
            <div className="ml-auto max-w-[80%] rounded-lg bg-green-50 border border-green-200 px-3 py-2 text-sm">
              <div className="text-xs text-gray-400 mb-1">You</div>
              <div className="whitespace-pre-wrap">{lastSentRef.current}</div>
            </div>
          </div>
        )}
        {typing && !chatState.answer && (
          <div className="mr-auto max-w-[80%] rounded-lg bg-white border px-3 py-2 text-sm animate-pulse">
            <div className="text-xs text-gray-400 mb-1">Assistant</div>
            <div className="h-3 w-24 bg-gray-200 rounded mb-2" />
            <div className="h-3 w-48 bg-gray-200 rounded" />
            <div className="mt-1 text-[10px] text-gray-400">typing…</div>
          </div>
        )}
        {/* Live streaming assistant bubble (appears after first token, before feedback stage) */}
        {typing && chatState.answer && !chatState.awaitingFeedback && (
          <div className="flex">
            <div className="mr-auto max-w-[80%] rounded-lg bg-white border px-3 py-2 text-sm">
              <div className="text-xs text-gray-400 mb-1">Assistant</div>
              <div className="whitespace-pre-wrap">
                {chatState.answer}<span className="animate-pulse opacity-70">▌</span>
              </div>
              <div className="mt-1 text-[10px] text-gray-400">streaming…</div>
            </div>
          </div>
        )}

        {/* Rating UI under the latest assistant message */}
        {chatState.answer && (
          <div className="mr-auto max-w-[80%]">
            {chatState.awaitingFeedback ? (
              <div className="rounded border bg-white p-3">
                <div className="font-medium mb-2">How was this answer?</div>
                <div className="flex items-center gap-2 mb-2">
                  {[1,2,3,4,5].map((r)=> (
                    <button
                      key={r}
                      onClick={()=>setChatState(appId, { rating: r })}
                      className={`px-3 py-1 rounded border ${chatState.rating===r ? 'bg-blue-600 text-white' : 'bg-white'}`}
                    >{r}</button>
                  ))}
                </div>
                <textarea
                  className="w-full border rounded px-3 py-2 text-sm"
                  placeholder="Optional comment"
                  value={chatState.comment}
                  onChange={(e)=>setChatState(appId, { comment: e.target.value })}
                  rows={3}
                />
                <div className="mt-2 flex gap-2">
                  <button
                    disabled={busy || chatState.rating == null}
                    onClick={onSubmitFeedback}
                    className="px-3 py-2 rounded bg-indigo-600 text-white disabled:opacity-50"
                  >Submit feedback</button>
                  <span className="text-xs text-gray-500 self-center">You must submit feedback before asking another question.</span>
                </div>
              </div>
            ) : null}
          </div>
        )}

        {/* Input inside chat history box, sticky at bottom */}
        <div className="sticky bottom-0 bg-gray-50 pt-2">
          <div className="flex gap-2">
            <input
              className="flex-1 border rounded px-3 py-2"
              placeholder={chatState.awaitingFeedback ? "Please submit feedback before asking another question" : "Ask something..."}
              value={chatState.lastMessage}
              onChange={(e)=>setChatState(appId, { lastMessage: e.target.value })}
              disabled={chatState.awaitingFeedback}
            />
            {/* Removed top_k control per user request; keeping logic defaulting to existing stored value. */}
            <button disabled={busy || chatState.awaitingFeedback || typing} onClick={onSend} className="px-3 py-2 rounded bg-green-600 text-white disabled:opacity-50">Send</button>
          </div>
        </div>
      </div>
    </div>
  )
}
