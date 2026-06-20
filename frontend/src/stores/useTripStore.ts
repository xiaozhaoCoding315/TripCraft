import { create } from 'zustand'
import type { AgentProgressEvent, MemoryItem, PlanSummary, TravelPlan } from '../types/travel'

export interface ChatMessage {
  role: 'user' | 'system'
  content: string
  timestamp: string
  loading?: boolean
}

interface TripState {
  plan?: TravelPlan
  events: AgentProgressEvent[]
  plans: PlanSummary[]
  memory: MemoryItem[]
  planning: boolean
  error?: string
  statusDetail: string
  chatMessages: Record<string, ChatMessage[]>
  // 方案对比状态
  comparison: { beforePlan: TravelPlan; afterPlan: TravelPlan; summary: string } | null

  setPlan: (plan?: TravelPlan) => void
  setPlanning: (planning: boolean) => void
  setError: (error?: string) => void
  addEvent: (event: AgentProgressEvent) => void
  setEvents: (events: AgentProgressEvent[]) => void
  setPlans: (plans: PlanSummary[]) => void
  setMemory: (memory: MemoryItem[]) => void
  setStatusDetail: (detail: string) => void
  setChatMessages: (planId: string, messages: ChatMessage[]) => void
  addChatMessage: (planId: string, message: ChatMessage) => void
  updateLastChatMessage: (planId: string, updater: (msg: ChatMessage) => ChatMessage) => void
  removeLastChatMessage: (planId: string) => void
  setComparison: (comp: TripState['comparison']) => void
  reset: () => void
  fullReset: () => void
}

export const useTripStore = create<TripState>((set) => ({
  events: [],
  plans: [],
  memory: [],
  planning: false,
  chatMessages: {},
  statusDetail: '',

  setPlan: (plan) => set({ plan }),
  setPlanning: (planning) => set({ planning }),
  setError: (error) => set({ error }),
  addEvent: (event) =>
    set((state) => {
      let statusDetail = state.statusDetail
      if (event.status === 'running') {
        statusDetail = event.message
      }
      return {
        events: [...state.events.slice(-99), event],
        statusDetail,
      }
    }),
  setEvents: (events) => set({ events }),
  setPlans: (plans) => set({ plans }),
  setMemory: (memory) => set({ memory }),
  setStatusDetail: (statusDetail) => set({ statusDetail }),

  setChatMessages: (planId, messages) =>
    set((state) => ({
      chatMessages: { ...state.chatMessages, [planId]: messages },
    })),

  addChatMessage: (planId, message) =>
    set((state) => ({
      chatMessages: {
        ...state.chatMessages,
        [planId]: [...(state.chatMessages[planId] || []), message],
      },
    })),

  updateLastChatMessage: (planId, updater) =>
    set((state) => {
      const msgs = state.chatMessages[planId] || []
      if (msgs.length === 0) return state
      const updated = [...msgs]
      updated[updated.length - 1] = updater(updated[updated.length - 1])
      return {
        chatMessages: { ...state.chatMessages, [planId]: updated },
      }
    }),

  removeLastChatMessage: (planId) =>
    set((state) => {
      const msgs = state.chatMessages[planId] || []
      return {
        chatMessages: { ...state.chatMessages, [planId]: msgs.slice(0, -1) },
      }
    }),

  comparison: null,

  setComparison: (comparison) => set({ comparison }),

  // 部分重置（保留 plans 和 memory）
  reset: () => set({ plan: undefined, events: [], error: undefined, planning: false, statusDetail: '', comparison: null }),

  // 完全重置（包括 plans、memory、chatMessages）
  fullReset: () => set({
    plan: undefined,
    events: [],
    plans: [],
    memory: [],
    planning: false,
    error: undefined,
    statusDetail: '',
    chatMessages: {},
  }),
}))
