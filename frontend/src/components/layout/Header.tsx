import { GlobalOutlined, LogoutOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { Button, Space, Tooltip, Typography } from 'antd'
import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useState } from 'react'

const { Text } = Typography

interface HeaderProps {
  planStatus?: 'idle' | 'planning' | 'complete' | 'error'
  statusText?: string
  onLogout?: () => void
}

const statusConfig = {
  idle: { text: '准备就绪', color: 'var(--text-muted)', pulse: false, icon: '○' },
  planning: { text: '规划中...', color: 'var(--neon-amber)', pulse: true, icon: '◉' },
  complete: { text: '已完成', color: 'var(--neon-green)', pulse: false, icon: '●' },
  error: { text: '出错了', color: 'var(--neon-rose)', pulse: false, icon: '⚠' },
}

export default function Header({ planStatus = 'idle', statusText, onLogout }: HeaderProps) {
  const [scrolled, setScrolled] = useState(false)
  const status = statusConfig[planStatus]
  const displayText = statusText || status.text

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <header
      className={`app-header ${scrolled ? 'scrolled' : ''}`}
    >
      {/* Logo section */}
      <Space size="middle">
        <motion.div
          whileHover={{ rotate: 15, scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
          style={{
            width: 42,
            height: 42,
            borderRadius: 12,
            background: planStatus === 'planning'
              ? 'linear-gradient(135deg, var(--neon-amber), var(--neon-cyan))'
              : 'linear-gradient(135deg, var(--neon-cyan), var(--neon-teal))',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: planStatus === 'planning'
              ? '0 0 30px rgba(251, 191, 36, 0.4)'
              : '0 0 20px rgba(34, 211, 240, 0.3)',
            cursor: 'pointer',
          }}
        >
          <ThunderboltOutlined style={{ fontSize: 22, color: '#0a0f1d' }} />
        </motion.div>
        <div>
          <Text
            strong
            className="glitch-text"
            style={{
              fontSize: 20,
              fontWeight: 700,
              background: 'linear-gradient(135deg, var(--neon-cyan), var(--neon-teal))',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              letterSpacing: '-0.5px',
            }}
          >
            TripCraft
          </Text>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: -3, letterSpacing: '0.5px' }}>
            MULTI-AGENT TRAVEL PLANNING
          </div>
        </div>
      </Space>

      {/* Status + Actions */}
      <Space size="middle">
        {/* Status badge */}
        <AnimatePresence mode="wait">
          <motion.div
            key={planStatus + displayText}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ duration: 0.3 }}
            className={planStatus === 'planning' ? 'status-ripple' : ''}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '6px 16px',
              borderRadius: 20,
              background:
                planStatus === 'planning' ? 'rgba(251, 191, 36, 0.1)'
                : planStatus === 'complete' ? 'rgba(74, 222, 128, 0.1)'
                : planStatus === 'error' ? 'rgba(251, 113, 133, 0.1)'
                : 'rgba(100, 116, 139, 0.1)',
              border: `1px solid ${status.color}40`,
              color: status.color,
            }}
          >
            {status.pulse && (
              <motion.div
                animate={{ scale: [1, 1.3, 1], opacity: [0.7, 1, 0.7] }}
                transition={{ duration: 1.5, repeat: Infinity }}
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: status.color,
                  boxShadow: `0 0 8px ${status.color}`,
                }}
              />
            )}
            {!status.pulse && (
              <span style={{
                width: 8, height: 8, borderRadius: '50%',
                background: status.color,
                boxShadow: `0 0 6px ${status.color}`,
              }} />
            )}
            <span style={{ fontSize: 13, fontWeight: 500 }}>
              {displayText}
            </span>
          </motion.div>
        </AnimatePresence>

        <Tooltip title="退出登录">
          <Button
            type="text"
            icon={<LogoutOutlined />}
            onClick={onLogout}
            style={{ color: 'var(--text-muted)' }}
          />
        </Tooltip>
      </Space>
    </header>
  )
}
