/**
 * WelcomeScreen v2 - Enhanced idle state landing page
 * Glass card with animated features, gradient text, responsive glow
 */

import { motion } from 'framer-motion'

const features = [
  { emoji: '🤖', label: 'AI 规划', color: '#22d3f0' },
  { emoji: '🗺️', label: '地图可视化', color: '#2dd4bf' },
  { emoji: '💬', label: '对话调整', color: '#a78bfa' },
  { emoji: '⚡', label: '实时进度', color: '#fbbf24' },
]

const container = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.12, delayChildren: 0.1 },
  },
}

const item = {
  hidden: { opacity: 0, y: 15 },
  visible: { opacity: 1, y: 0 },
}

export default function WelcomeScreen() {
  return (
    <div
      style={{
        textAlign: 'center',
        padding: '60px 32px',
        position: 'relative',
      }}
    >
      {/* Decorative ring */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: 320,
          height: 320,
          borderRadius: '50%',
          border: '1px solid rgba(34, 211, 240, 0.08)',
          pointerEvents: 'none',
        }}
      />

      {/* Animated icon */}
      <motion.div
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
        style={{ fontSize: 72, marginBottom: 20, position: 'relative' }}
      >
        <span style={{ filter: 'drop-shadow(0 0 20px rgba(34,211,240,0.3))' }}>
          ✈️
        </span>
      </motion.div>

      {/* Title */}
      <h2
        style={{
          fontSize: 32,
          fontWeight: 700,
          margin: '0 0 10px',
          background: 'linear-gradient(135deg, #22d3f0, #a78bfa, #2dd4bf)',
          backgroundSize: '200% 200%',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
          animation: 'energyFlow 4s linear infinite',
          letterSpacing: '-1px',
          lineHeight: 1.3,
        }}
      >
        开始您的智能旅行规划
      </h2>

      {/* Subtitle */}
      <p style={{
        color: 'var(--text-muted)',
        fontSize: 15,
        marginBottom: 32,
        maxWidth: 400,
        margin: '0 auto 32px',
      }}>
        基于多智能体协作的 AI 旅行规划系统
      </p>

      {/* Feature tags */}
      <motion.div
        variants={container}
        initial="hidden"
        animate="visible"
        style={{
          display: 'flex',
          gap: 12,
          flexWrap: 'wrap',
          justifyContent: 'center',
        }}
      >
        {features.map((f) => (
          <motion.span
            key={f.label}
            variants={item}
            whileHover={{ scale: 1.05, y: -2 }}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              padding: '10px 20px',
              background: 'rgba(15, 23, 42, 0.7)',
              border: `1px solid ${f.color}30`,
              borderRadius: 24,
              fontSize: 14,
              color: '#cbd5e1',
              backdropFilter: 'blur(12px)',
              cursor: 'default',
              transition: 'all 0.3s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = `${f.color}60`
              e.currentTarget.style.boxShadow = `0 0 20px ${f.color}20`
              e.currentTarget.style.color = f.color
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = `${f.color}30`
              e.currentTarget.style.boxShadow = 'none'
              e.currentTarget.style.color = '#cbd5e1'
            }}
          >
            <span style={{ fontSize: 18 }}>{f.emoji}</span>
            {f.label}
          </motion.span>
        ))}
      </motion.div>
    </div>
  )
}
