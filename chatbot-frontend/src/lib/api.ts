import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const api = axios.create({ baseURL: BASE_URL })

export async function uploadFile(file: File, app_id: string, chunk_size = 800) {
  const form = new FormData()
  form.append('file', file)
  form.append('app_id', app_id)
  form.append('chunk_size', String(chunk_size))
  const { data } = await api.post('/ingest/file', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function chat(message: string, top_k = 5, app_id?: string) {
  const { data } = await api.post('/chat/', { message, top_k, app_id })
  return data as { response: string; sources: any[] }
}

// Streaming chat (Server-Sent Events via POST fallback using fetch streaming)
export async function chatStream(params: { message: string; top_k?: number; app_id?: string; onToken: (t: string)=>void; signal?: AbortSignal; }): Promise<{ answer: string; sources: any[] }> {
  const { message, top_k = 5, app_id, onToken, signal } = params
  // Use raw fetch so we can access the ReadableStream
  const res = await fetch(`${BASE_URL}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, top_k, app_id }),
    signal,
  })
  if (!res.ok || !res.body) {
    throw new Error(`Streaming request failed: ${res.status}`)
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finalAnswer = ''
  let finalSources: any[] = []
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    // Split into SSE event frames separated by blank line
    const frames = buffer.split(/\n\n/)
    buffer = frames.pop() || ''
    for (const frame of frames) {
      // Ignore keep-alives / comments
      if (!/^(data:|event:)/m.test(frame)) continue
      const lines = frame.split('\n')
      let eventName: string | null = null
      const dataPayload: string[] = []
      for (const line of lines) {
        if (line.startsWith('event:')) eventName = line.slice(6).trim()
        else if (line.startsWith('data:')) dataPayload.push(line.slice(5).trim())
      }
      const dataStr = dataPayload.join('\n')
      if (!dataStr) continue
      if (eventName === 'done') {
        try {
          const json = JSON.parse(dataStr)
          finalAnswer = json.answer || finalAnswer
          finalSources = json.sources || finalSources
        } catch {
          // swallow JSON parse errors for robustness
        }
      } else {
        // Treat as incremental content
        onToken(dataStr)
      }
    }
  }
  return { answer: finalAnswer, sources: finalSources }
}

export async function search(query: string, top_k = 5, app_id?: string) {
  const { data } = await api.post('/search/', { query, top_k, app_id })
  return data as { results: any[] }
}

export type FeedbackPayload = {
  app_id: string
  query: string
  response: string
  rating: number
  comment?: string
  sources?: any[]
}

export async function submitFeedback(payload: FeedbackPayload) {
  const { data } = await api.post('/feedback/', payload)
  return data as { status: string }
}

export type FeedbackItem = {
  id: number
  app_id: string
  query: string
  response: string
  rating: number
  comment?: string
  sources?: any[]
  created_at?: string
}

export async function fetchFeedback(app_id?: string, limit = 100) {
  const { data } = await api.get('/feedback/', { params: { app_id, limit } })
  return data as { items: FeedbackItem[] }
}

export async function clearFeedback(app_id?: string) {
  const { data } = await api.delete('/feedback/', { params: { app_id, confirm: true } })
  return data as { removed: number }
}

export async function fetchAppIds() {
  const { data } = await api.get('/admin/apps')
  return (data?.app_ids ?? []) as string[]
}

export async function createOrUpdateApp(app_id: string, display_name?: string, description?: string) {
  const { data } = await api.post('/admin/apps', null, { params: { app_id, display_name, description } })
  return data as { app: { app_id: string; display_name?: string; description?: string; created_at?: string } }
}

export async function fetchApp(app_id: string) {
  const { data } = await api.get(`/admin/apps/${encodeURIComponent(app_id)}`)
  return data as { app: { app_id: string; display_name?: string; description?: string; created_at?: string } }
}

export type AppDocument = {
  id: number
  app_id: string
  filename: string
  size_bytes?: number
  chunk_size?: number
  chunk_count?: number
  model?: string
  created_at?: string
}

export async function listDocuments(app_id?: string, limit = 200) {
  const { data } = await api.get('/documents/', { params: { app_id, limit } })
  return data as { items: AppDocument[] }
}

export async function deleteDocument(doc_id: number) {
  const { data } = await api.delete(`/documents/${doc_id}`, { params: { confirm: true } })
  return data as { deleted: boolean }
}

export async function reindexDocument(doc_id: number) {
  const { data } = await api.post(`/documents/${doc_id}/reindex`)
  return data as { status: string; result?: any }
}

// Chat history
export type ChatTurn = {
  id: number
  app_id: string
  user_message: string
  assistant_answer: string
  sources: any[]
  created_at: string
}

export async function fetchHistory(app_id?: string, limit = 200) {
  const { data } = await api.get('/history/', { params: { app_id, limit } })
  return data as ChatTurn[]
}

export async function clearHistory(app_id: string) {
  const { data } = await api.delete('/history/', { params: { app_id, confirm: true } })
  return data as { deleted: number }
}

// Analytics
export type AnalyticsSummary = {
  app_id: string
  total_requests: number
  feedback_count: number
  average_rating: number | null
  ratings: { rating_1: number; rating_2: number; rating_3: number; rating_4: number; rating_5: number }
}

export async function fetchAnalyticsSummary(app_id: string) {
  const { data } = await api.get('/analytics/summary', { params: { app_id } })
  return data as AnalyticsSummary
}
