export type AgentName =
  | 'orchestrator'
  | 'weather'
  | 'transport'
  | 'accommodation'
  | 'attraction'
  | 'itinerary'
  | 'critic'

export type AgentStatus = 'queued' | 'running' | 'success' | 'error' | 'retrying'

export interface TravelerProfile {
  adults: number
  children: number
  seniors: number
  mobility_notes?: string
}

export interface TravelPlanRequest {
  destination: string
  start_date: string
  days: number
  budget?: number
  departure_city?: string
  travelers: TravelerProfile
  interests: string[]
  preferences?: string
}

export interface SourceRef {
  type: 'amap' | 'rag' | 'llm' | 'template'
  label: string
  url?: string
}

export interface GeoPoint {
  lng?: number | null
  lat?: number | null
  address?: string | null
}

export interface ItineraryItem {
  id: string
  time: string
  type: 'transport' | 'attraction' | 'meal' | 'hotel' | 'rest' | 'note'
  title: string
  description: string
  location?: GeoPoint | null
  cost?: number | null
  duration_minutes?: number | null
  source_refs: SourceRef[]
}

export interface DayPlan {
  day: number
  date?: string | null
  title: string
  weather_summary?: string | null
  items: ItineraryItem[]
  estimated_cost?: number | null
  pace: 'relaxed' | 'balanced' | 'intensive'
}

export interface CriticComment {
  dimension: 'physical' | 'time' | 'budget' | 'weather' | 'data' | 'overall'
  severity: 'info' | 'warning' | 'critical'
  message: string
  suggestion?: string | null
}

export interface Revision {
  version: number
  passed: boolean
  comments: CriticComment[]
  summary: string
}

export interface TravelPlan {
  plan_id: string
  destination: string
  version: number
  days: DayPlan[]
  total_estimated_cost?: number | null
  revisions: Revision[]
  raw_context: Record<string, unknown>
}

export interface AgentProgressEvent {
  agent: AgentName
  status: AgentStatus
  message: string
  payload: Record<string, unknown>
}

export interface PlanSummary {
  plan_id: string
  destination: string
  departure_city?: string | null
  version: number
  days: number
  total_estimated_cost?: number | null
  created_at: string
  updated_at: string
}

export interface MemoryItem {
  key: string
  value: string
  category: 'traveler' | 'pace' | 'budget' | 'hotel' | 'transport' | 'interest' | 'avoid' | 'general'
  source: 'request' | 'adjustment' | 'system' | 'llm'
  confidence: number
  updated_at?: string | null
}

export interface PersistedPlanResponse {
  plan: TravelPlan
  request?: TravelPlanRequest | null
  events: AgentProgressEvent[]
  adjustments: Array<{ instruction: string; summary: string; created_at: string }>
  created_at?: string | null
  updated_at?: string | null
}

export interface RagStatusItem {
  job_id: string
  collection: string
  status: string
  inserted: number
  message?: string | null
  created_at: string
  updated_at: string
}
