/**
 * TripCraft API Client
 *
 * 封装 HTTP 和 WebSocket 请求，自动附加 JWT Token。
 */

import axios from 'axios'
import type {
  AgentProgressEvent,
  MemoryItem,
  PersistedPlanResponse,
  PlanSummary,
  RagStatusItem,
  TravelPlan,
  TravelPlanRequest,
} from '../types/travel'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api/v1',
  timeout: 60000,
})

// 请求拦截器：自动附加 JWT Token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('tripcraft_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：401 跳转登录
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('tripcraft_token')
      localStorage.removeItem('tripcraft_user')
      // 避免循环跳转
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export interface PlanResponse {
  plan: TravelPlan
  events: AgentProgressEvent[]
}

export interface AdjustmentResponse {
  plan: TravelPlan
  summary: string
  events: AgentProgressEvent[]
}

export interface AuthResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface UserResponse {
  user_id: string
  username: string
  email?: string
}

export const authAPI = {
  login: (username: string, password: string) =>
    api.post<unknown, AuthResponse>('/auth/login', { username, password }),
  register: (username: string, password: string, email?: string) =>
    api.post<unknown, UserResponse>('/auth/register', { username, password, email }),
  me: () => api.get<unknown, UserResponse>('/auth/me'),
  logout: () => {
    localStorage.removeItem('tripcraft_token')
    localStorage.removeItem('tripcraft_user')
  },
}

export const travelAPI = {
  createPlan: (request: TravelPlanRequest) => api.post<unknown, PlanResponse>('/plans', request),
  adjustPlan: (plan: TravelPlan, instruction: string) =>
    api.post<unknown, AdjustmentResponse>('/plans/adjust', { plan, instruction }),
  listPlans: (limit = 30) => api.get<unknown, PlanSummary[]>('/plans', { params: { limit } }),
  getPlan: (planId: string) => api.get<unknown, PersistedPlanResponse>(`/plans/${planId}`),
  getEvents: (planId: string) => api.get<unknown, AgentProgressEvent[]>(`/plans/${planId}/events`),
  listMemory: () => api.get<unknown, MemoryItem[]>('/memory'),
  deleteMemory: (key: string) => api.delete<unknown, { deleted: boolean }>(`/memory/${encodeURIComponent(key)}`),
  ragStatus: () => api.get<unknown, RagStatusItem[]>('/rag/status'),
  deletePlan: (planId: string) => api.delete<unknown, { deleted: boolean }>(`/plans/${planId}`),
  exportPreview: (planId: string) =>
    api.get<unknown, { filename: string; content: string }>(`/plans/${planId}/export/preview`),
  getChatMessages: (planId: string) =>
    api.get<unknown, any[]>(`/plans/${planId}/chat`),
  saveChatMessages: (planId: string, messages: any[]) =>
    api.post<unknown, { saved: boolean }>(`/plans/${planId}/chat`, messages),
}

/**
 * WebSocket 流式规划
 */
export function streamPlan(
  request: TravelPlanRequest,
  handlers: {
    onProgress: (event: AgentProgressEvent) => void
    onComplete: (plan: TravelPlan, events: AgentProgressEvent[]) => void
    onError: (message: string) => void
  },
) {
  const token = localStorage.getItem('tripcraft_token') || ''
  const baseUrl = import.meta.env.VITE_WS_URL || `ws://${window.location.host}/api/v1/plans/stream`
  const wsUrl = token ? `${baseUrl}?token=${encodeURIComponent(token)}` : baseUrl
  const ws = new WebSocket(wsUrl)
  ws.onopen = () => ws.send(JSON.stringify(request))
  ws.onmessage = (message) => {
    const data = JSON.parse(message.data)
    if (data.type === 'progress') handlers.onProgress(data.event)
    if (data.type === 'complete') handlers.onComplete(data.plan, data.events || [])
    if (data.type === 'error') handlers.onError(data.message || '规划失败')
  }
  ws.onerror = () => handlers.onError('WebSocket 连接失败')
  return () => ws.close()
}

/**
 * WebSocket 流式调整
 */
export function streamAdjust(
  plan: TravelPlan,
  instruction: string,
  handlers: {
    onProgress: (event: AgentProgressEvent) => void
    onComplete: (plan: TravelPlan, summary: string) => void
    onError: (message: string) => void
  },
) {
  const token = localStorage.getItem('tripcraft_token') || ''
  const baseUrl =
    import.meta.env.VITE_WS_URL?.replace('/plans/stream', '/plans/adjust/stream') ||
    `ws://${window.location.host}/api/v1/plans/adjust/stream`
  const wsUrl = token ? `${baseUrl}?token=${encodeURIComponent(token)}` : baseUrl
  const ws = new WebSocket(wsUrl)
  ws.onopen = () => ws.send(JSON.stringify({ plan, instruction }))
  ws.onmessage = (message) => {
    const data = JSON.parse(message.data)
    if (data.type === 'progress') handlers.onProgress(data)
    if (data.type === 'complete') handlers.onComplete(data.plan, data.summary)
    if (data.type === 'error') handlers.onError(data.message || '调整失败')
  }
  ws.onerror = () => handlers.onError('WebSocket 连接失败')
  return () => ws.close()
}
