import { useEffect, useMemo, useState } from 'react'
import { fetchAnalyticsSummary, AnalyticsSummary, clearHistory, clearFeedback } from '../lib/api'
import { useAppStore } from '../store/useAppStore'

export default function AnalyticsPanel() {
  const appId = useAppStore((s) => s.appId)
  const [data, setData] = useState<AnalyticsSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      if (!appId) { setData(null); return }
      setLoading(true)
      setError(null)
      try {
        const res = await fetchAnalyticsSummary(appId)
        if (!cancelled) setData(res)
      } catch (e: any) {
        if (!cancelled) setError(e?.response?.data?.detail || e.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [appId])

  async function onClearChat() {
    if (!appId) return
    if (!confirm('Clear ALL chat history for this app?')) return
    try {
      await clearHistory(appId)
      // refresh summary after clearing
      const res = await fetchAnalyticsSummary(appId)
      setData(res)
    } catch (e: any) {
      alert(e?.response?.data?.detail || e.message)
    }
  }

  async function onClearFeedback() {
    if (!appId) return
    if (!confirm('Clear ALL feedback for this app?')) return
    try {
      await clearFeedback(appId)
      // refresh summary after clearing
      const res = await fetchAnalyticsSummary(appId)
      setData(res)
    } catch (e: any) {
      alert(e?.response?.data?.detail || e.message)
    }
  }

  const ratingsArr = useMemo(() => data ? [
    { label: '1', value: data.ratings.rating_1 },
    { label: '2', value: data.ratings.rating_2 },
    { label: '3', value: data.ratings.rating_3 },
    { label: '4', value: data.ratings.rating_4 },
    { label: '5', value: data.ratings.rating_5 },
  ] : [], [data])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="font-medium">Overview</div>
        <div className="text-xs text-gray-500">
          {loading ? 'Loading…' : error ? <span className="text-red-600">{error}</span> : null}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <StatCard title="Total requests" value={data?.total_requests ?? 0} />
        <StatCard title="Feedback submitted" value={data?.feedback_count ?? 0} />
        <StatCard title="Average rating" value={data?.average_rating != null ? data!.average_rating.toFixed(2) : '—'} />
      </div>

      <div className="flex justify-end">
        <button className="inline-flex items-center gap-1 px-3 py-2 rounded border text-red-600 border-red-600 hover:bg-red-50" onClick={onClearFeedback}>
          <svg aria-hidden width="14" height="14" viewBox="0 0 24 24" fill="currentColor" className="text-red-600">
            <path d="M9 3h6a1 1 0 0 1 1 1v1h5v2h-1l-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 7H3V5h5V4a1 1 0 0 1 1-1Zm2 3h2V5h-2v1ZM7 9l1 12h8l1-12H7Z"/>
          </svg>
          <span>Clear feedback</span>
        </button>
      </div>

      <div>
        <div className="font-medium mb-2">Ratings distribution</div>
        <div className="rounded border bg-white p-3">
          <div className="flex items-end gap-2 h-40">
            {ratingsArr.map((r) => (
              <div key={r.label} className="flex-1 flex flex-col items-center">
                <div className="w-full bg-indigo-200 rounded-t" style={{ height: `${Math.max(4, r.value * 12)}px` }} />
                <div className="text-xs text-gray-600 mt-1">{r.label}</div>
                <div className="text-xs text-gray-900">{r.value}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ title, value }: { title: string; value: number | string }) {
  return (
    <div className="rounded border bg-white p-4">
      <div className="text-sm text-gray-500">{title}</div>
      <div className="text-2xl font-semibold">{value}</div>
    </div>
  )
}
