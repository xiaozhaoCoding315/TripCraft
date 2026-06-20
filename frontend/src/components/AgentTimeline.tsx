import { CheckCircleOutlined, LoadingOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { motion, AnimatePresence } from 'framer-motion'
import type { AgentProgressEvent } from '../types/travel'

interface Props {
  events: AgentProgressEvent[]
}

const agentColors: Record<string, string> = {
  orchestrator: '#a78bfa',
  weather: '#22d3f0',
  transport: '#2dd4bf',
  accommodation: '#fbbf24',
  attraction: '#4ade80',
  itinerary: '#a78bfa',
  critic: '#fb7185',
}

export default function AgentTimeline({ events }: Props) {
  if (events.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '48px 0', color: '#64748b' }}>
        <motion.div
          animate={{ scale: [1, 1.05, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
          style={{ fontSize: 40, marginBottom: 14 }}
        >
          ⏳
        </motion.div>
        <div style={{ fontSize: 14 }}>等待智能体启动...</div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <AnimatePresence initial={false}>
        {events.slice(-40).map((event, idx) => {
          const color = agentColors[event.agent] || '#22d3f0'
          const isRunning = event.status === 'running'
          const isSuccess = event.status === 'success'
          const isError = event.status === 'error'

          return (
            <motion.div
              key={`${event.agent}-${idx}`}
              initial={{ opacity: 0, x: -10, height: 0 }}
              animate={{ opacity: 1, x: 0, height: 'auto' }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 12,
                padding: '10px 14px',
                background: isRunning ? `${color}08` : 'transparent',
                borderRadius: 10,
                borderLeft: `3px solid ${
                  isRunning ? color : isSuccess ? color + '60' : isError ? '#fb7185' : 'transparent'
                }`,
              }}
            >
              {/* Status icon */}
              <div style={{ flexShrink: 0, paddingTop: 1 }}>
                {isRunning ? (
                  <LoadingOutlined style={{ color, fontSize: 15 }} spin />
                ) : isSuccess ? (
                  <CheckCircleOutlined style={{ color: '#4ade80', fontSize: 15 }} />
                ) : isError ? (
                  <CloseCircleOutlined style={{ color: '#fb7185', fontSize: 15 }} />
                ) : (
                  <div style={{
                    width: 15,
                    height: 15,
                    borderRadius: '50%',
                    border: `2px solid ${color}40`,
                  }} />
                )}
              </div>

              {/* Content */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
                  <span style={{
                    fontSize: 12,
                    fontWeight: 600,
                    color: isRunning ? color : '#cbd5e1',
                    textTransform: 'capitalize',
                  }}>
                    {event.agent}
                  </span>
                  {isRunning && (
                    <span style={{
                      fontSize: 10,
                      padding: '1px 8px',
                      borderRadius: 10,
                      background: `${color}15`,
                      color: color,
                    }}>
                      RUNNING
                    </span>
                  )}
                  {isSuccess && (
                    <span style={{
                      fontSize: 10,
                      padding: '1px 8px',
                      borderRadius: 10,
                      background: 'rgba(74,222,128,0.15)',
                      color: '#4ade80',
                    }}>
                      DONE
                    </span>
                  )}
                </div>
                <div style={{
                  fontSize: 12,
                  color: '#94a3b8',
                  lineHeight: 1.5,
                  wordBreak: 'break-word',
                }}>
                  {event.message}
                </div>
              </div>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}
