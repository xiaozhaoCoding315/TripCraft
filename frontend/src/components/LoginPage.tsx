/**
 * LoginPage v3 - Split layout
 * Left: Feature showcase with animated tags
 * Right: Login/Register card with clean inputs
 */

import { LockOutlined, UserOutlined, MailOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { Button, Card, Form, Input, message, Tabs, Typography } from 'antd'
import { useState } from 'react'
import { motion } from 'framer-motion'
import { authAPI } from '../api/client'

const { Title, Text } = Typography

interface Props {
  onLoginSuccess: () => void
}

const features = [
  { emoji: '🤖', label: 'AI 多智能体协作规划', desc: '6个AI智能体并行工作，实时协作生成个性化旅行方案' },
  { emoji: '🗺️', label: '地图路线可视化', desc: '集成高德地图，行程路径一目了然' },
  { emoji: '💬', label: '对话式行程调整', desc: '像聊天一样对AI说"慢一点"或"加个景点"' },
  { emoji: '⚡', label: '实时进度追踪', desc: 'WebSocket流式推送，看到每个Agent的工作状态' },
]

const container = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.15, delayChildren: 0.2 } },
}
const itemVariant = {
  hidden: { opacity: 0, x: -20 },
  visible: { opacity: 1, x: 0 },
}

// Shared input style to fix the "black overlay" issue
const inputStyle: React.CSSProperties = {
  background: 'rgba(30, 41, 59, 0.6)',
  border: '1px solid rgba(34, 211, 240, 0.25)',
  borderRadius: 10,
  color: '#e2e8f0',
  padding: '10px 12px',
  height: 44,
  fontSize: 14,
  transition: 'all 0.3s ease',
}
const prefixStyle: React.CSSProperties = { color: '#22d3f0', fontSize: 15 }

export default function LoginPage({ onLoginSuccess }: Props) {
  const [loading, setLoading] = useState(false)
  const [tab, setTab] = useState<'login' | 'register'>('login')

  async function handleLogin(values: { username: string; password: string }) {
    setLoading(true)
    try {
      const res = await authAPI.login(values.username, values.password)
      localStorage.setItem('tripcraft_token', res.access_token)
      localStorage.setItem('tripcraft_user', values.username)
      message.success('登录成功！')
      onLoginSuccess()
    } catch {
      message.error('登录失败，请检查用户名和密码')
    } finally {
      setLoading(false)
    }
  }

  async function handleRegister(values: { username: string; password: string; email?: string }) {
    setLoading(true)
    try {
      await authAPI.register(values.username, values.password, values.email)
      message.success('注册成功！请登录')
      setTab('login')
    } catch {
      message.error('注册失败，用户名可能已存在')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #060b14 0%, #0d1525 40%, #111827 100%)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Ambient background effects */}
      <div className="grid-floor" />
      <div style={{
        position: 'absolute', width: 600, height: 600, borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(34,211,240,0.07) 0%, transparent 70%)',
        top: '-10%', right: '-5%', filter: 'blur(80px)', pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute', width: 400, height: 400, borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(167,139,250,0.05) 0%, transparent 70%)',
        bottom: '-5%', left: '40%', filter: 'blur(60px)', pointerEvents: 'none',
      }} />

      {/* ========== LEFT: Feature Showcase ========== */}
      <div style={{
        flex: '1 1 50%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        padding: '60px 80px',
        position: 'relative',
        zIndex: 1,
      }}>
        {/* Logo */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20 }}
        >
          <div style={{
            width: 52, height: 52, borderRadius: 14,
            background: 'linear-gradient(135deg, #22d3f0, #2dd4bf)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 8px 30px rgba(34,211,240,0.35)',
          }}>
            <ThunderboltOutlined style={{ fontSize: 26, color: '#060b14' }} />
          </div>
          <div>
            <span style={{
              fontSize: 26, fontWeight: 700,
              background: 'linear-gradient(135deg, #22d3f0, #a78bfa)',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}>
              TripCraft
            </span>
            <div style={{ fontSize: 11, color: '#64748b', letterSpacing: 1, marginTop: -2 }}>
              INTELLIGENT TRAVEL PLANNING
            </div>
          </div>
        </motion.div>

        {/* Hero text */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.15 }}
        >
          <h1 style={{
            fontSize: 36, fontWeight: 700, lineHeight: 1.3, margin: '0 0 12px',
            background: 'linear-gradient(135deg, #e2e8f0, #22d3f0)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}>
            开始您的<br />智能旅行规划
          </h1>
          <p style={{ color: '#94a3b8', fontSize: 15, margin: '0 0 40px', lineHeight: 1.6, maxWidth: 400 }}>
            基于 AI 多智能体协作系统，6个专业Agent并行工作，
            为您生成个性化、可调整的完整旅行方案。
          </p>
        </motion.div>

        {/* Feature list */}
        <motion.div
          variants={container}
          initial="hidden"
          animate="visible"
          style={{ display: 'flex', flexDirection: 'column', gap: 18 }}
        >
          {features.map((f) => (
            <motion.div
              key={f.label}
              variants={itemVariant}
              whileHover={{ x: 6 }}
              style={{
                display: 'flex', alignItems: 'flex-start', gap: 14,
                padding: '14px 18px',
                background: 'rgba(15,23,42,0.5)',
                border: '1px solid rgba(34,211,240,0.08)',
                borderRadius: 14,
                transition: 'all 0.3s ease',
                cursor: 'default',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'rgba(34,211,240,0.2)'
                e.currentTarget.style.background = 'rgba(34,211,240,0.05)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'rgba(34,211,240,0.08)'
                e.currentTarget.style.background = 'rgba(15,23,42,0.5)'
              }}
            >
              <span style={{ fontSize: 28, flexShrink: 0 }}>{f.emoji}</span>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: '#e2e8f0', marginBottom: 3 }}>
                  {f.label}
                </div>
                <div style={{ fontSize: 12, color: '#64748b', lineHeight: 1.5 }}>
                  {f.desc}
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Bottom tagline */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2 }}
          style={{
            marginTop: 40,
            display: 'flex', gap: 10, flexWrap: 'wrap',
          }}
        >
          {['AI 规划', '地图可视化', '对话调整', '实时进度'].map((tag, i) => (
            <span key={tag} style={{
              padding: '5px 14px', borderRadius: 20,
              background: 'rgba(34,211,240,0.08)',
              border: '1px solid rgba(34,211,240,0.15)',
              fontSize: 12, color: '#94a3b8',
            }}>
              {['🤖','🗺️','💬','⚡'][i]} {tag}
            </span>
          ))}
        </motion.div>
      </div>

      {/* ========== RIGHT: Login Card ========== */}
      <div style={{
        flex: '0 0 520px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px',
        position: 'relative',
        zIndex: 1,
      }}>
        <motion.div
          initial={{ opacity: 0, x: 30, scale: 0.97 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1], delay: 0.2 }}
          style={{ width: '100%', maxWidth: 420 }}
        >
          <Card
            style={{
              width: '100%',
              background: 'rgba(15, 23, 42, 0.8)',
              backdropFilter: 'blur(24px) saturate(180%)',
              WebkitBackdropFilter: 'blur(24px) saturate(180%)',
              border: '1px solid rgba(34, 211, 240, 0.18)',
              borderRadius: 20,
              boxShadow: '0 20px 60px rgba(0, 0, 0, 0.5), 0 0 50px rgba(34,211,240,0.06)',
            }}
            bodyStyle={{ padding: '32px 30px' }}
          >
            {/* Card header */}
            <div style={{ textAlign: 'center', marginBottom: 24 }}>
              <Title level={3} style={{ color: '#e2e8f0', marginBottom: 4, fontWeight: 700, fontSize: 22 }}>
                {tab === 'login' ? '欢迎回来' : '创建账号'}
              </Title>
              <Text style={{ color: '#64748b', fontSize: 13 }}>
                {tab === 'login' ? '登录以查看您的行程' : '注册后即可开始规划旅行'}
              </Text>
            </div>

            <Tabs
              activeKey={tab}
              onChange={(key) => setTab(key as 'login' | 'register')}
              centered
              size="small"
              style={{ marginBottom: 12 }}
              items={[
                {
                  key: 'login',
                  label: <span style={{ fontSize: 14, fontWeight: 500 }}>登录</span>,
                  children: (
                    <Form onFinish={handleLogin} layout="vertical" size="large" style={{ marginTop: 8 }}>
                      <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]} style={{ marginBottom: 16 }}>
                        <Input
                          prefix={<UserOutlined style={prefixStyle} />}
                          placeholder="用户名"
                          style={inputStyle}
                        />
                      </Form.Item>
                      <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]} style={{ marginBottom: 22 }}>
                        <Input.Password
                          prefix={<LockOutlined style={prefixStyle} />}
                          placeholder="密码"
                          style={inputStyle}
                        />
                      </Form.Item>
                      <Form.Item style={{ marginBottom: 0 }}>
                        <Button type="primary" htmlType="submit" block loading={loading} size="large"
                          style={{
                            height: 46, borderRadius: 12,
                            background: 'linear-gradient(135deg, #22d3f0, #06b6d4)',
                            border: 'none', fontWeight: 600, fontSize: 15,
                            boxShadow: '0 4px 20px rgba(34,211,240,0.3)',
                          }}
                        >
                          登录
                        </Button>
                      </Form.Item>
                    </Form>
                  ),
                },
                {
                  key: 'register',
                  label: <span style={{ fontSize: 14, fontWeight: 500 }}>注册</span>,
                  children: (
                    <Form onFinish={handleRegister} layout="vertical" size="large" style={{ marginTop: 8 }}>
                      <Form.Item name="username" rules={[
                        { required: true, message: '请输入用户名' },
                        { min: 3, message: '用户名至少3个字符' },
                      ]} style={{ marginBottom: 16 }}>
                        <Input
                          prefix={<UserOutlined style={prefixStyle} />}
                          placeholder="用户名"
                          style={inputStyle}
                        />
                      </Form.Item>
                      <Form.Item name="email" style={{ marginBottom: 16 }}>
                        <Input
                          prefix={<MailOutlined style={{ color: '#a78bfa', fontSize: 15 }} />}
                          placeholder="邮箱（可选）"
                          style={{
                            ...inputStyle,
                            border: '1px solid rgba(167, 139, 250, 0.2)',
                          }}
                        />
                      </Form.Item>
                      <Form.Item name="password" rules={[
                        { required: true, message: '请输入密码' },
                        { min: 6, message: '密码至少6个字符' },
                      ]} style={{ marginBottom: 22 }}>
                        <Input.Password
                          prefix={<LockOutlined style={prefixStyle} />}
                          placeholder="密码"
                          style={inputStyle}
                        />
                      </Form.Item>
                      <Form.Item style={{ marginBottom: 0 }}>
                        <Button type="primary" htmlType="submit" block loading={loading} size="large"
                          style={{
                            height: 46, borderRadius: 12,
                            background: 'linear-gradient(135deg, #2dd4bf, #14b8a6)',
                            border: 'none', fontWeight: 600, fontSize: 15,
                            boxShadow: '0 4px 20px rgba(45,212,191,0.3)',
                          }}
                        >
                          注册
                        </Button>
                      </Form.Item>
                    </Form>
                  ),
                },
              ]}
            />

            <div style={{
              textAlign: 'center', marginTop: 16,
              padding: '10px 0', borderTop: '1px solid rgba(34,211,240,0.08)',
            }}>
              <Text style={{ color: '#475569', fontSize: 11 }}>
                基于 AI 多智能体协作 · 生成个性化旅行方案
              </Text>
            </div>
          </Card>
        </motion.div>
      </div>
    </div>
  )
}
