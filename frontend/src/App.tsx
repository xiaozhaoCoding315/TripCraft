/**
 * TripCraft v2 - Main Application Component
 * Supports guest mode (browse without login) + authenticated mode
 * Three-layer space: Background → Midground → Foreground
 */

import { ConfigProvider, Layout, message, theme } from 'antd'
import { lazy, Suspense, useEffect, useRef, useState, useCallback } from 'react'
import { PlusOutlined } from '@ant-design/icons'
import { motion, AnimatePresence } from 'framer-motion'
import { streamPlan, streamAdjust, travelAPI } from './api/client'
import PlanningForm from './components/PlanningForm'
import DashboardLayout from './components/DashboardLayout'
import ContextPanel from './components/ContextPanel'
import TripContextPanel from './components/TripContextPanel'
import WelcomeScreen from './components/WelcomeScreen'
import PlanningScreen from './components/PlanningScreen'
import TripDashboard from './components/TripDashboard'
import AssistantPanel from './components/AssistantPanel'
import LoginPage from './components/LoginPage'
import { AnimatedBackground, Header, FloatingAgentOrb } from './components/layout'
import ErrorBoundary from './components/ErrorBoundary'
import MemoryPanel from './components/MemoryPanel'
import { useTripStore } from './stores/useTripStore'
import type { TravelPlanRequest } from './types/travel'
import './styles/variables.css'
import './styles/utilities.css'
import './styles/animations.css'
import './styles/effects.css'
import './styles/app.css'
import { pluginRegistry, QuickFactsPlugin, WeatherDetailPlugin, CostDashboardPlugin } from './plugins'

const AdjustmentChat = lazy(() => import('./components/AdjustmentChat'))

// 注册内置插件（QuickFacts → WeatherDetail → CostDashboard 按侧边栏顺序）
pluginRegistry.registerAll([QuickFactsPlugin, WeatherDetailPlugin, CostDashboardPlugin])

interface AppProps {
  loggedIn: boolean
  onLogout: () => void
  onLoginSuccess: () => void
}

export default function App({ loggedIn, onLogout, onLoginSuccess }: AppProps) {
  const {
    plan,
    events,
    plans,
    memory,
    planning,
    error,
    statusDetail,
    setPlan,
    setEvents,
    addEvent,
    setPlans,
    setMemory,
    setPlanning,
    setError,
    setStatusDetail,
    fullReset,
  } = useTripStore()

  const closeStream = useRef<(() => void) | null>(null)
  const [currentPlanId, setCurrentPlanId] = useState<string | null>(null)
  const [chatPanelOpen, setChatPanelOpen] = useState(false)
  const [showLogin, setShowLogin] = useState(false)
  const mountedRef = useRef(false)
  const prevLoggedInRef = useRef(loggedIn)

  const activePhase: 'idle' | 'planning' | 'result' =
    planning ? 'planning' : plan ? 'result' : 'idle'

  // Load data when authenticated (only on first mount or when logging in)
  useEffect(() => {
    const wasLoggedOut = !prevLoggedInRef.current && loggedIn
    prevLoggedInRef.current = loggedIn

    if (!loggedIn) {
      // Guest mode: clear data
      fullReset()
      mountedRef.current = false
      return
    }

    if (mountedRef.current && !wasLoggedOut) return
    mountedRef.current = true

    // Load fresh data for authenticated user
    travelAPI.listPlans().then(setPlans).catch(() => {})
    travelAPI.listMemory().then(setMemory).catch(() => {})
  }, [loggedIn, fullReset, setPlans, setMemory])

  // Also refresh when logging in
  useEffect(() => {
    if (!loggedIn) return
    travelAPI.listPlans().then(setPlans).catch(() => {})
    travelAPI.listMemory().then(setMemory).catch(() => {})
  }, [loggedIn, setPlans, setMemory])

  const refreshSideData = useCallback(async () => {
    if (!loggedIn) return
    try {
      const [p, m] = await Promise.all([
        travelAPI.listPlans().catch(() => []),
        travelAPI.listMemory().catch(() => []),
      ])
      setPlans(p)
      setMemory(m)
    } catch {}
  }, [loggedIn, setPlans, setMemory])

  const loadPlan = useCallback(async (planId: string) => {
    try {
      const data = await travelAPI.getPlan(planId)
      setPlan(data.plan)
      setEvents(data.events)
      setCurrentPlanId(planId)
      setChatPanelOpen(true)
      message.success('已加载历史行程')
    } catch {
      message.error('加载历史行程失败')
    }
  }, [setPlan, setEvents])

  const deletePlan = useCallback(async (planId: string) => {
    try {
      await travelAPI.deletePlan(planId)
      message.success('行程已删除')
      await refreshSideData()
      if (currentPlanId === planId) handleNewPlan()
    } catch {
      message.error('删除失败')
    }
  }, [currentPlanId, refreshSideData])

  const startPlanning = useCallback((request: TravelPlanRequest) => {
    if (!loggedIn) {
      message.warning('请先登录后再创建行程')
      setShowLogin(true)
      return
    }

    closeStream.current?.()
    fullReset()
    setPlanning(true)
    setStatusDetail('正在连接服务...')
    setCurrentPlanId(null)

    closeStream.current = streamPlan(request, {
      onProgress: addEvent,
      onComplete: (nextPlan, nextEvents) => {
        setPlan(nextPlan)
        setEvents(nextEvents)
        setPlanning(false)
        setStatusDetail('行程规划完成')
        setCurrentPlanId(nextPlan.plan_id)
        setChatPanelOpen(true)
        refreshSideData()
        message.success('行程规划完成！')
      },
      onError: (msg) => {
        setError(msg)
        setPlanning(false)
        setStatusDetail('')
        message.error(msg)
      },
    })
  }, [loggedIn, fullReset, addEvent, setPlan, setEvents, setPlanning, setStatusDetail, setChatPanelOpen, refreshSideData, setError])

  const handleNewPlan = useCallback(() => {
    fullReset()
    setEvents([])
    setError(undefined)
    setStatusDetail('')
    setCurrentPlanId(null)
    setChatPanelOpen(false)
  }, [fullReset, setEvents, setError, setStatusDetail, setChatPanelOpen])

  const handleEditPlan = useCallback(() => {
    setChatPanelOpen(true)
  }, [setChatPanelOpen])

  const handleExport = useCallback(async (format: 'json' | 'markdown' | 'text' | 'preview') => {
    if (!plan) return
    try {
      const token = localStorage.getItem('tripcraft_token') || ''
      const isPreview = format === 'preview'
      const exportFormat = isPreview ? 'markdown' : format
      const endpoint = isPreview
        ? `/api/v1/plans/${plan.plan_id}/export/preview`
        : `/api/v1/plans/${plan.plan_id}/export/${exportFormat}`
      const resp = await fetch(endpoint, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: '导出失败' }))
        message.error((err as any).detail || '导出失败')
        return
      }
      const data = await resp.json()
      const mimeMap: Record<string, string> = { json: 'application/json', markdown: 'text/markdown', text: 'text/plain', preview: 'text/markdown' }
      const blob = new Blob([data.content], { type: mimeMap[format] || 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = data.filename; a.click()
      URL.revokeObjectURL(url)
      message.success(isPreview ? 'AI 预览导出成功' : '导出成功')
    } catch {
      message.error('导出失败')
    }
  }, [plan])

  const startAdjust = useCallback((instruction: string) => {
    if (!plan) return

    closeStream.current?.()
    setChatPanelOpen(true)
    const beforePlan = { ...plan }  // 保存修改前的方案（浅拷贝用于对比）

    closeStream.current = streamAdjust(plan, instruction, {
      onProgress: (event) => {
        useTripStore.getState().updateLastChatMessage(plan.plan_id, (msg) => ({
          ...msg,
          content: event.message || '处理中...',
        }))
      },
      onComplete: (updatedPlan, summary) => {
        // 不自动应用 → 触发方案对比
        useTripStore.getState().updateLastChatMessage(plan.plan_id, (msg) => ({
          ...msg,
          content: summary || '调整已完成，请查看方案对比',
          loading: false,
        }))
        // 设置对比状态，等用户确认
        useTripStore.getState().setComparison({
          beforePlan: beforePlan,
          afterPlan: updatedPlan,
          summary: summary || '',
        })
      },
      onError: (errMsg) => {
        useTripStore.getState().removeLastChatMessage(plan.plan_id)
        message.error(errMsg)
      },
    })
  }, [plan, setChatPanelOpen])

  const handleLoginSuccess = useCallback(() => {
    setShowLogin(false)
    onLoginSuccess()
  }, [onLoginSuccess])

  const getStatusText = () => {
    if (planning) return statusDetail || '规划中'
    if (plan) return '已完成'
    if (error) return '出错了'
    return '准备就绪'
  }

  const getPlanStatus = (): 'idle' | 'planning' | 'complete' | 'error' => {
    if (planning) return 'planning'
    if (plan) return 'complete'
    if (error) return 'error'
    return 'idle'
  }

  // ============================================
  // LOGIN MODAL: Show login page as overlay
  // ============================================
  if (showLogin) {
    return (
      <>
        <LoginPage onLoginSuccess={handleLoginSuccess} />
        <button
          onClick={() => setShowLogin(false)}
          style={{
            position: 'fixed',
            top: 20,
            right: 20,
            zIndex: 100,
            background: 'rgba(15,23,42,0.8)',
            border: '1px solid rgba(34,211,240,0.15)',
            borderRadius: 10,
            color: '#94a3b8',
            padding: '8px 16px',
            cursor: 'pointer',
            fontSize: 14,
            backdropFilter: 'blur(12px)',
          }}
        >
          ← 返回浏览
        </button>
      </>
    )
  }

  // ============================================
  // PLANNING PHASE: Full-screen immersive view
  // ============================================
  if (activePhase === 'planning') {
    return (
      <ConfigProvider
        theme={{
          algorithm: theme.darkAlgorithm,
          token: {
            colorPrimary: '#22d3f0',
            borderRadius: 12,
            fontFamily: 'Inter, system-ui, sans-serif',
            colorBgContainer: 'rgba(15, 23, 42, 0.6)',
            colorBorder: 'rgba(34, 211, 240, 0.15)',
          },
        }}
      >
        <AnimatedBackground phase="planning" />
        <div className="layer-midground">
          <Layout className="app-shell" style={{ background: 'transparent' }}>
            <Header planStatus="planning" statusText={getStatusText()} onLogout={onLogout} />
            <ErrorBoundary>
              <Layout.Content className="app-content" style={{ padding: 0 }}>
                <PlanningScreen events={events} />
              </Layout.Content>
            </ErrorBoundary>
          </Layout>
        </div>
        <div className="layer-foreground">
          <FloatingAgentOrb events={events} planning={true} />
        </div>
      </ConfigProvider>
    )
  }

  // ============================================
  // IDLE / RESULT PHASES: Dashboard layout
  // ============================================
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#22d3f0',
          colorSuccess: '#4ade80',
          colorWarning: '#fbbf24',
          colorError: '#fb7185',
          borderRadius: 12,
          fontFamily: 'Inter, system-ui, sans-serif',
          colorBgContainer: 'rgba(15, 23, 42, 0.6)',
          colorBorder: 'rgba(34, 211, 240, 0.15)',
        },
      }}
    >
      <AnimatedBackground phase={activePhase} />

      <div className="layer-midground">
        <Layout className="app-shell" style={{ background: 'transparent' }}>
          <Header planStatus={getPlanStatus()} statusText={getStatusText()} onLogout={onLogout} />
          <ErrorBoundary>
            <AnimatePresence mode="wait">
              <motion.div
                key={activePhase}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
              >
                <Layout.Content className="app-content">
                  {/* Guest mode: show login CTA above the welcome screen */}
                  {!loggedIn && activePhase === 'idle' && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      style={{
                        textAlign: 'center',
                        padding: '12px 0',
                        marginBottom: 8,
                      }}
                    >
                      <span style={{ color: '#94a3b8', fontSize: 13, marginRight: 12 }}>
                        🔓 以访客身份浏览 · 登录后可创建行程
                      </span>
                      <button
                        onClick={() => setShowLogin(true)}
                        style={{
                          background: 'linear-gradient(135deg, #22d3f0, #2dd4bf)',
                          border: 'none',
                          borderRadius: 20,
                          color: '#060b14',
                          padding: '6px 20px',
                          cursor: 'pointer',
                          fontSize: 13,
                          fontWeight: 600,
                          boxShadow: '0 2px 12px rgba(34,211,240,0.3)',
                        }}
                      >
                        登录 / 注册
                      </button>
                    </motion.div>
                  )}

                  <DashboardLayout
                    phase={activePhase}
                    historyPanel={
                      loggedIn ? (
                        <div>
                          {/* 插件面板 */}
                          {activePhase === 'result' && plan && pluginRegistry.getBySlot('sidebar').length > 0 && (
                            <div style={{ marginBottom: 12 }}>
                              {pluginRegistry.renderSlot('sidebar', { plan })}
                            </div>
                          )}
                          <MemoryPanel
                            plans={plans}
                            memory={memory}
                            onReload={refreshSideData}
                            onLoadPlan={loadPlan}
                            onDeletePlan={deletePlan}
                            currentPlanId={currentPlanId}
                          />
                        </div>
                      ) : (
                        <div className="glass-card" style={{ padding: 20, textAlign: 'center' }}>
                          <div style={{ fontSize: 32, marginBottom: 10 }}>🔐</div>
                          <div style={{ fontSize: 13, color: '#94a3b8', marginBottom: 12 }}>
                            登录后可查看历史行程
                          </div>
                          <button
                            onClick={() => setShowLogin(true)}
                            className="btn-base btn-primary"
                            style={{ fontSize: 13, padding: '8px 20px' }}
                          >
                            登录 / 注册
                          </button>
                        </div>
                      )
                    }
                    contextPanel={
                      <ContextPanel phase={activePhase}>
                        {activePhase === 'idle' && (
                          <div className="card circuit-border">
                            <div className="card-header">
                              <PlusOutlined /> 创建新行程
                            </div>
                            <PlanningForm loading={planning} onSubmit={startPlanning} />
                          </div>
                        )}
                        {activePhase === 'result' && plan && (
                          <TripContextPanel
                            plan={plan} plans={plans} memory={memory}
                            currentPlanId={currentPlanId}
                            onLoadPlan={loadPlan} onDeletePlan={deletePlan}
                            onNewPlan={handleNewPlan} onEditPlan={handleEditPlan} onExport={handleExport}
                          />
                        )}
                      </ContextPanel>
                    }
                    mainStage={
                      <main className="main-content">
                        {activePhase === 'idle' && <WelcomeScreen />}
                        {activePhase === 'result' && plan && (
                          <TripDashboard
                            plan={plan}
                            onPlanChange={(p) => { setPlan(p); refreshSideData() }}
                            onNewPlan={handleNewPlan} onEditPlan={handleEditPlan}
                            onExport={handleExport} onAdjust={startAdjust}
                          />
                        )}
                      </main>
                    }
                    assistantPanel={
                      activePhase === 'result' && plan ? (
                        <AssistantPanel open={chatPanelOpen} onToggle={() => setChatPanelOpen(v => !v)}>
                          {chatPanelOpen && (
                            <Suspense fallback={<div className="spinner" />}>
                              <AdjustmentChat
                                plan={plan}
                                onPlanChange={(p) => { setPlan(p); refreshSideData() }}
                                onAdjust={startAdjust}
                              />
                            </Suspense>
                          )}
                        </AssistantPanel>
                      ) : null
                    }
                  />
                </Layout.Content>
              </motion.div>
            </AnimatePresence>
          </ErrorBoundary>
        </Layout>
      </div>

      {/* Foreground layer */}
      <div className="layer-foreground">
        <FloatingAgentOrb events={events} planning={false} />
        <AnimatePresence>
          {error && (
            <motion.div
              className="error-toast"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
            >
              <span>{error}</span>
              <button onClick={() => { setError(undefined); refreshSideData() }} style={{ background: 'none', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 6, color: '#94a3b8', cursor: 'pointer', padding: '4px 12px', fontSize: 12 }}>
                🔄 重试
              </button>
              <button onClick={() => setError(undefined)}>✕</button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </ConfigProvider>
  )
}
