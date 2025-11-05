import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ChatState = {
  lastMessage: string
  answer: string
  sources: any[]
  expanded: Record<number, boolean>
  awaitingFeedback: boolean
  rating: number | null
  comment: string
  topK: number
}

export const defaultChatState: ChatState = {
  lastMessage: '',
  answer: '',
  sources: [],
  expanded: {},
  awaitingFeedback: false,
  rating: null,
  comment: '',
  topK: 5,
}

type Store = {
  byApp: Record<string, ChatState>
  setStateFor: (appId: string, partial: Partial<ChatState>) => void
  resetStateFor: (appId: string) => void
}

export const useChatStore = create<Store>()(
  persist(
    (set, get) => ({
      byApp: {},
      setStateFor: (appId, partial) =>
        set((s) => ({ byApp: { ...s.byApp, [appId]: { ...(s.byApp[appId] || defaultChatState), ...partial } } })),
      resetStateFor: (appId) => set((s) => {
        const next = { ...s.byApp }
        next[appId] = { ...defaultChatState }
        return { byApp: next }
      }),
    }),
    { name: 'chat-state' }
  )
)
