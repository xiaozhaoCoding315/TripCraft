/**
 * PlanningScreen v2 - Full-screen planning view
 * Left: Animated agent nodes with neon glow
 * Right: Real-time event timeline
 */

import { motion } from 'framer-motion'
import AgentTimeline from './AgentTimeline'
import type { AgentProgressEvent } from '../types/travel'

interface Props {
  events: AgentProgressEvent[]
}

const agentInfo: Record<string, { icon: string; color: string; label: string }> = {
  weather: { icon: '🌤️', color: '#22d3f0', label: 'Weather' },
  transport: { icon: '🚄', color: '#2dd4bf', label: 'Transport' },
  accommodation: { icon: '🏨', color: '#fbbf24', label: 'Accommodation' },
  attraction: { icon: '🏛️', color: '#4ade80', label: 'Attraction' },
  itinerary: { icon: '📋', color: '#a78bfa', label: 'Itinerary' },
  critic: { icon: '🔍', color: '#fb7185', label: 'Critic' },
}

const agentList = Object.entries(agentInfo)

const container = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08 } },
}

const cardVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: { opacity: 1, x: 0 },
}

export default function PlanningScreen({ events }: Props) {
  const runningCount = agentList.filter(([key]) =>
    events.find(e => e.agent === key)?.status === 'running'
  ).length
  const successCount = agentList.filter(([key]) =>
    events.find(e => e.agent === key)?.status === 'success'
  ).length

  return (
    <div
      style={{
        display: 'flex',
        minHeight: 'calc(100vh - 60px)',
        background: 'transparent',
      }}
    >
      {/* Left: Agent status panel */}
      <div
        style={{
          width: 340,
          flexShrink: 0,
          borderRight: '1px solid rgba(34, 211, 240, 0.12)',
          padding: 28,
          overflowY: 'auto',
        }}
        className="custom-scrollbar"
      >
        {/* Header */}
        <div style={{ marginBottom: 24 }}>
          <motion.h2
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
              fontSize: 22,
              fontWeight: 700,
              color: '#e2e8f0',
              marginBottom: 6,
              background: 'linear-gradient(135deg, #22d3f0, #a78bfa)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}
          >
            ⚡ AI 正在为您规划
          </motion.h2>
          <p style={{ fontSize: 13, color: '#64748b', margin: 0 }}>
            多个智能体协作收集数据，请稍候...
          </p>
          {/* Overall progress */}
          <div style={{ marginTop: 12 }}>
            <div style={{
              height: 3,
              background: 'rgba(26, 37, 56, 0.6)',
              borderRadius: 2,
              overflow: 'hidden',
            }}>
              <motion.div
                animate={{ width: `${(successCount / agentList.length) * 100}%` }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
                style={{
                  height: '100%',
                  background: 'linear-gradient(90deg, #22d3f0, #2dd4bf)',
                  borderRadius: 2,
                  boxShadow: '0 0 10px rgba(34,211,240,0.4)',
                }}
              />
            </div>
            <div style={{
              fontSize: 11,
              color: '#64748b',
              marginTop: 4,
              display: 'flex',
              justifyContent: 'space-between',
            }}>
              <span>{successCount}/{agentList.length} 已完成</span>
              {runningCount > 0 && (
                <span style={{ color: '#fbbf24' }}>{runningCount} 运行中</span>
              )}
            </div>
          </div>
        </div>

        {/* Agent nodes */}
        <motion.div
          variants={container}
          initial="hidden"
          animate="visible"
          style={{ display: 'flex', flexDirection: 'column', gap: 10 }}
        >
          {agentList.map(([key, info]) => {
            const event = events.find(e => e.agent === key)
            const status = event?.status || 'queued'
            const isRunning = status === 'running'
            const isSuccess = status === 'success'
            const isError = status === 'error'

            return (
              <motion.div
                key={key}
                variants={cardVariants}
                className={isRunning ? 'status-ripple' : ''}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 14,
                  padding: '14px 16px',
                  background: isRunning
                    ? `${info.color}12`
                    : isSuccess
                    ? `${info.color}08`
                    : 'rgba(15, 23, 42, 0.5)',
                  border: `1px solid ${
                    isRunning ? info.color + '40'
                    : isSuccess ? info.color + '30'
                    : isError ? '#fb718540'
                    : 'rgba(34, 211, 240, 0.08)'
                  }`,
                  borderRadius: 14,
                  transition: 'all 0.4s ease',
                  boxShadow: isRunning ? `0 0 20px ${info.color}20` : 'none',
                }}
              >
                {/* Agent icon */}
                <motion.div
                  animate={isRunning ? {
                    boxShadow: [
                      `0 0 8px ${info.color}40`,
                      `0 0 20px ${info.color}60`,
                      `0 0 8px ${info.color}40`,
                    ],
                  } : {}}
                  transition={{ duration: 1.5, repeat: Infinity }}
                  style={{
                    width: 44,
                    height: 44,
                    borderRadius: 12,
                    background: isSuccess
                      ? `${info.color}20`
                      : isRunning
                      ? `${info.color}15`
                      : 'rgba(15, 23, 42, 0.6)',
                    border: `2px solid ${isSuccess ? info.color : isRunning ? info.color + '80' : 'rgba(34,211,240,0.1)'}`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 20,
                  }}
                >
                  {isSuccess ? '✓' : info.icon}
                </motion.div>

                {/* Agent info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: 14,
                    fontWeight: 600,
                    color: isSuccess ? info.color : isRunning ? '#fbbf24' : '#cbd5e1',
                    textTransform: 'capitalize',
                  }}>
                    {info.label}
                  </div>
                  <div style={{
                    fontSize: 11,
                    color: isRunning ? info.color : '#64748b',
                    marginTop: 2,
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}>
                    {isRunning ? event?.message || 'Processing...'
                      : isSuccess ? 'Completed'
                      : isError ? event?.message || 'Error'
                      : 'Waiting...'}
                  </div>
                </div>

                {/* Status indicator */}
                {isRunning && (
                  <motion.div
                    animate={{ scale: [1, 1.3, 1], opacity: [0.7, 1, 0.7] }}
                    transition={{ duration: 1.2, repeat: Infinity }}
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: '50%',
                      background: info.color,
                      boxShadow: `0 0 12px ${info.color}`,
                      flexShrink: 0,
                    }}
                  />
                )}
                {isSuccess && (
                  <span style={{
                    color: '#4ade80',
                    fontSize: 16,
                    fontWeight: 700,
                    flexShrink: 0,
                  }}>
                    ●
                  </span>
                )}
              </motion.div>
            )
          })}
        </motion.div>
      </div>

      {/* Right: Real-time timeline */}
      <div style={{ flex: 1, padding: 28, overflowY: 'auto' }} className="custom-scrollbar">
        <div style={{ marginBottom: 16 }}>
          <h3 style={{
            fontSize: 16,
            fontWeight: 600,
            color: '#e2e8f0',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}>
            <span style={{ color: '#22d3f0' }}>◉</span> 实时进度
          </h3>
        </div>
        <AgentTimeline events={events} />
      </div>
    </div>
  )
}
