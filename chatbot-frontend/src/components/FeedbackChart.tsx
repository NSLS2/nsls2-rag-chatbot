import { useEffect, useMemo, useState } from 'react'
import { fetchFeedback, FeedbackItem } from '../lib/api'
import { useAppStore } from '../store/useAppStore'
import {
  Chart as ChartJS,
  TimeScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from 'chart.js'
import 'chartjs-adapter-date-fns'
import { Line } from 'react-chartjs-2'

ChartJS.register(TimeScale, LinearScale, PointElement, LineElement, Tooltip, Legend)

export default function FeedbackChart() {
  const appId = useAppStore((s) => s.appId)
  const [items, setItems] = useState<FeedbackItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const res = await fetchFeedback(appId, 200)
        if (!cancelled) setItems(res.items || [])
      } catch (e: any) {
        if (!cancelled) setError(e?.response?.data?.detail || e.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [appId])

  const data = useMemo(() => {
    const points = (items || [])
      .filter(it => typeof it.rating === 'number' && it.created_at)
      .map(it => ({ x: new Date(it.created_at as string), y: it.rating }))
      .sort((a,b)=> (a.x as any) - (b.x as any))
    return {
      datasets: [
        {
          label: `Rating (${appId})`,
          data: points,
          borderColor: 'rgb(79,70,229)',
          backgroundColor: 'rgba(79,70,229,0.2)',
          tension: 0.2,
        }
      ]
    }
  }, [items, appId])

  const options = useMemo(() => ({
    responsive: true,
    plugins: { legend: { display: true } },
    scales: {
      x: { type: 'time' as const, time: { unit: 'minute' as const } },
      y: { min: 1, max: 5, ticks: { stepSize: 1 } }
    }
  }), [])

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="font-medium">Feedback over time</div>
        {loading && <div className="text-xs text-gray-500">Loading…</div>}
        {error && <div className="text-xs text-red-600">{error}</div>}
      </div>
      <div className="rounded border bg-white p-3">
        <Line data={data} options={options} />
      </div>
    </div>
  )
}
