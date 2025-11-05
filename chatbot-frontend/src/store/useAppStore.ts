import { create } from 'zustand'

type AppState = {
  appId: string
  setAppId: (v: string) => void
  busy: boolean
  setBusy: (v: boolean) => void
  appIds: string[]
  setAppIds: (ids: string[]) => void
}

export const useAppStore = create<AppState>((set) => ({
  appId: localStorage.getItem('appId') || 'default',
  setAppId: (v) => { localStorage.setItem('appId', v); set({ appId: v }) },
  busy: false,
  setBusy: (v) => set({ busy: v }),
  appIds: [],
  setAppIds: (ids) => set({ appIds: ids }),
}))
