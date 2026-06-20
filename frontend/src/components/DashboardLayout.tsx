/**
 * DashboardLayout v2 - Enhanced three-zone layout with depth layers
 *
 * Left: Collapsible side drawer (history/memory)
 * Center: Context panel + Main stage (2-zone vertical stack)
 * Right: Assistant panel (slide-in)
 */

import { ReactNode } from 'react'

interface Props {
  phase: 'idle' | 'planning' | 'result'
  historyPanel: ReactNode
  contextPanel: ReactNode
  mainStage: ReactNode
  assistantPanel?: ReactNode
}

export default function DashboardLayout({
  historyPanel,
  contextPanel,
  mainStage,
  assistantPanel,
}: Props) {
  return (
    <div className="dashboard-layout">
      {/* Left: History/Memory sidebar */}
      <aside
        style={{
          width: 280,
          flexShrink: 0,
          position: 'sticky',
          top: 80,
          alignSelf: 'flex-start',
          maxHeight: 'calc(100vh - 120px)',
          overflowY: 'auto',
        }}
        className="custom-scrollbar"
      >
        <div
          className="glass-card"
          style={{
            padding: 16,
          }}
        >
          {historyPanel}
        </div>
      </aside>

      {/* Center: Context + Main Stage */}
      <div className="dashboard-main">
        {/* Context panel (planning form or trip summary) */}
        {contextPanel}

        {/* Main stage (welcome, itinerary, map, etc.) */}
        {mainStage}
      </div>

      {/* Right: Assistant chat panel */}
      {assistantPanel}
    </div>
  )
}
