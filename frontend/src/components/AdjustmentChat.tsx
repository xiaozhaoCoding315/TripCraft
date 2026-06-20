/**
 * AdjustmentChat v4 - Comparison approval + no duplicate messages
 */

import { SendOutlined, BulbOutlined, CheckOutlined, CloseOutlined, LoadingOutlined, SwapOutlined } from '@ant-design/icons'
import { Button, Input, message, Tag } from 'antd'
import { useEffect, useRef, useState, useCallback } from 'react'
import type { TravelPlan } from '../types/travel'
import { useTripStore } from '../stores/useTripStore'
import { travelAPI } from '../api/client'

interface Props {
  plan?: TravelPlan
  onPlanChange: (plan: TravelPlan) => void
  onAdjust: (instruction: string) => void
}

const quickSuggestions = [
  { label: '放慢节奏', icon: '🐢' },
  { label: '降低预算', icon: '💰' },
  { label: '增加购物时间', icon: '🛍️' },
  { label: '替换酒店类型', icon: '🏨' },
  { label: '增加美食推荐', icon: '🍜' },
  { label: '优化交通路线', icon: '🚇' },
]

const EMPTY_MSGS: import('../stores/useTripStore').ChatMessage[] = []

export default function AdjustmentChat({ plan, onPlanChange, onAdjust }: Props) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const submittingRef = useRef(false)

  const chatMessages = useTripStore((s) => {
    if (!plan?.plan_id) return EMPTY_MSGS
    return s.chatMessages[plan.plan_id] ?? EMPTY_MSGS
  })
  const addChatMessage = useTripStore((s) => s.addChatMessage)
  const updateLastChatMessage = useTripStore((s) => s.updateLastChatMessage)
  const removeLastChatMessage = useTripStore((s) => s.removeLastChatMessage)
  const comparison = useTripStore((s) => s.comparison)
  const setComparison = useTripStore((s) => s.setComparison)

  // 加载远程聊天记录
  const loadedPlanRef = useRef<string | null>(null)
  useEffect(() => {
    if (!plan?.plan_id || plan.plan_id === loadedPlanRef.current) return
    loadedPlanRef.current = plan.plan_id
    travelAPI.getChatMessages(plan.plan_id).then((msgs: any[]) => {
      if (msgs && msgs.length > 0) {
        useTripStore.getState().setChatMessages(plan.plan_id, msgs)
      }
    }).catch(() => {})
  }, [plan?.plan_id])

  // 聊天记录变更时持久化到后端
  const saveTimerRef = useRef<ReturnType<typeof setTimeout>>()
  useEffect(() => {
    if (!plan?.plan_id || chatMessages.length === 0) return
    clearTimeout(saveTimerRef.current)
    saveTimerRef.current = setTimeout(() => {
      travelAPI.saveChatMessages(plan.plan_id, chatMessages).catch(() => {})
    }, 1500) // debounce 1.5s
    return () => clearTimeout(saveTimerRef.current)
  }, [chatMessages, plan?.plan_id])

  // 监听最后一条消息的 loading 状态
  useEffect(() => {
    const lastMsg = chatMessages[chatMessages.length - 1]
    if (lastMsg && !lastMsg.loading && loading) {
      setLoading(false)
      submittingRef.current = false
    }
  }, [chatMessages, loading])

  // 自动滚动
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages, comparison])

  function handleAccept() {
    if (!comparison) return
    onPlanChange(comparison.afterPlan)
    addChatMessage(plan!.plan_id, {
      role: 'system',
      content: '✅ 已采用新方案',
      timestamp: new Date().toLocaleTimeString(),
    })
    setComparison(null)
    message.success('已应用调整方案')
  }

  function handleReject() {
    if (!comparison) return
    addChatMessage(plan!.plan_id, {
      role: 'system',
      content: '已保留原方案',
      timestamp: new Date().toLocaleTimeString(),
    })
    setComparison(null)
  }

  function submit() {
    if (!plan || !input.trim() || submittingRef.current || comparison) return
    submittingRef.current = true

    const instruction = input.trim()
    const timestamp = new Date().toLocaleTimeString()

    addChatMessage(plan.plan_id, { role: 'user', content: instruction, timestamp })
    setInput('')
    setLoading(true)

    addChatMessage(plan.plan_id, {
      role: 'system',
      content: '正在分析您的需求...',
      timestamp: new Date().toLocaleTimeString(),
      loading: true,
    })

    onAdjust(instruction)
  }

  function handleSuggestionClick(label: string) {
    if (submittingRef.current || comparison) return
    setInput(label)
  }

  // 计算对比数据 + 具体diff
  const beforePlan = comparison?.beforePlan
  const afterPlan = comparison?.afterPlan
  const beforeCost = beforePlan?.total_estimated_cost || plan?.total_estimated_cost || 0
  const afterCost = afterPlan?.total_estimated_cost || 0
  const beforeItems = beforePlan?.days?.reduce((s, d) => s + d.items.length, 0) || 0
  const afterItems = afterPlan?.days?.reduce((s, d) => s + d.items.length, 0) || 0

  // 对比具体项目变化
  type DiffItem = { day: number; title: string; type: string; action: string }
  const diffs: DiffItem[] = []
  if (beforePlan && afterPlan) {
    const beforeMap = new Map<string, string>()
    beforePlan.days.forEach(d => d.items.forEach(i => beforeMap.set(i.id, i.title)))
    const afterMap = new Map<string, string>()
    afterPlan.days.forEach(d => d.items.forEach(i => afterMap.set(i.id, i.title)))

    // 新增的
    afterPlan.days.forEach(d => d.items.forEach(i => {
      if (!beforeMap.has(i.id)) diffs.push({ day: d.day, title: i.title, type: i.type, action: '新增' })
    }))
    // 移除的
    beforePlan.days.forEach(d => d.items.forEach(i => {
      if (!afterMap.has(i.id)) diffs.push({ day: d.day, title: i.title, type: i.type, action: '移除' })
    }))
    // 费用变化
    beforePlan.days.forEach(d => d.items.forEach(bi => {
      const ai = afterPlan.days.flatMap(dd => dd.items).find(a => a.id === bi.id)
      if (ai && ai.cost !== bi.cost) {
        diffs.push({ day: d.day, title: bi.title, type: bi.type, action: `费用 ¥${bi.cost || 0} → ¥${ai.cost || 0}` })
      }
    }))
  }

  const typeEmoji: Record<string, string> = { transport: '🚄', attraction: '🎡', meal: '🍜', hotel: '🏨', rest: '☕', note: '📌' }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* ===== 方案对比卡片 ===== */}
      {comparison && (
        <div style={{
          padding: 16, borderRadius: 14,
          background: 'rgba(45, 212, 191, 0.08)',
          border: '1px solid rgba(45, 212, 191, 0.3)',
          boxShadow: '0 0 24px rgba(45,212,191,0.12)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
            <SwapOutlined style={{ color: '#2dd4bf', fontSize: 16 }} />
            <span style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0' }}>方案调整预览</span>
          </div>

          {/* 对比数字 */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: 10, marginBottom: 14 }}>
            <div style={{ textAlign: 'center', padding: 12, background: 'rgba(0,0,0,0.3)', borderRadius: 12 }}>
              <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4 }}>修改前</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#e2e8f0' }}>¥{beforeCost.toLocaleString()}</div>
              <div style={{ fontSize: 10, color: '#475569' }}>{comparison.beforePlan.days.length}天 · {beforeItems}项</div>
            </div>
            <span style={{ color: '#2dd4bf', fontSize: 24, alignSelf: 'center' }}>→</span>
            <div style={{
              textAlign: 'center', padding: 12, borderRadius: 12,
              background: 'rgba(45,212,191,0.12)', border: '1px solid rgba(45,212,191,0.3)',
            }}>
              <div style={{ fontSize: 11, color: '#2dd4bf', marginBottom: 4 }}>修改后</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#2dd4bf' }}>¥{afterCost.toLocaleString()}</div>
              <div style={{ fontSize: 10, color: '#5eead4' }}>{comparison.afterPlan.days.length}天 · {afterItems}项</div>
            </div>
          </div>

          {comparison.summary && (
            <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 14, lineHeight: 1.6, padding: '8px 12px', background: 'rgba(0,0,0,0.2)', borderRadius: 8 }}>
              💡 {comparison.summary}
            </div>
          )}

          {/* 变化标注 — 具体diff */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 11, color: '#64748b', marginBottom: 8 }}>📝 具体变化：</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: diffs.length > 0 ? 10 : 0 }}>
              {beforeCost !== afterCost && (
                <Tag style={{ fontSize: 10, background: 'rgba(251,191,36,0.1)', border: '1px solid rgba(251,191,36,0.2)', color: '#fbbf24', borderRadius: 10 }}>
                  费用 {afterCost > beforeCost ? '+' : ''}¥{(afterCost - beforeCost).toLocaleString()}
                </Tag>
              )}
              {beforeItems !== afterItems && (
                <Tag style={{ fontSize: 10, background: 'rgba(34,211,240,0.1)', border: '1px solid rgba(34,211,240,0.2)', color: '#22d3f0', borderRadius: 10 }}>
                  项目 {afterItems > beforeItems ? '+' : ''}{afterItems - beforeItems}个
                </Tag>
              )}
              <Tag style={{ fontSize: 10, background: 'rgba(167,139,250,0.1)', border: '1px solid rgba(167,139,250,0.2)', color: '#a78bfa', borderRadius: 10 }}>
                版本 v{comparison.afterPlan.version}
              </Tag>
            </div>
            {/* 逐条diff */}
            {diffs.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 140, overflowY: 'auto' }}>
                {diffs.slice(0, 10).map((d, i) => (
                  <div key={i} style={{
                    display: 'flex', alignItems: 'center', gap: 6, fontSize: 11,
                    padding: '4px 10px', borderRadius: 6,
                    background: d.action.includes('新增') ? 'rgba(74,222,128,0.08)' : d.action.includes('移除') ? 'rgba(251,113,133,0.08)' : 'rgba(34,211,240,0.06)',
                  }}>
                    <span style={{ color: d.action.includes('新增') ? '#4ade80' : d.action.includes('移除') ? '#fb7185' : '#22d3f0', fontWeight: 600, flexShrink: 0 }}>
                      {d.action.includes('新增') ? '+' : d.action.includes('移除') ? '−' : '~'}
                    </span>
                    <span style={{ color: '#64748b', flexShrink: 0 }}>D{d.day}</span>
                    <span>{(typeEmoji[d.type] || '📍')} {d.title.slice(0, 14)}</span>
                    <span style={{ color: '#475569', marginLeft: 'auto', flexShrink: 0, fontSize: 10 }}>
                      {d.action}
                    </span>
                  </div>
                ))}
                {diffs.length > 10 && (
                  <div style={{ fontSize: 10, color: '#475569', textAlign: 'center' }}>
                    ...还有 {diffs.length - 10} 处变化
                  </div>
                )}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <Button onClick={handleAccept} type="primary" block
              style={{
                background: 'linear-gradient(135deg, #2dd4bf, #14b8a6)', border: 'none',
                borderRadius: 10, fontWeight: 600, height: 40,
              }}
            >
              <CheckOutlined /> 采用新方案
            </Button>
            <Button onClick={handleReject} block
              style={{
                background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 10, color: '#94a3b8', height: 40,
              }}
            >
              <CloseOutlined /> 保留原方案
            </Button>
          </div>
        </div>
      )}

      {/* ===== 快捷建议 ===== */}
      {!comparison && (
        <div>
          <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 8 }}>
            <BulbOutlined style={{ marginRight: 4 }} />快捷指令（点击填入）
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {quickSuggestions.map((s) => (
              <Tag key={s.label} onClick={() => handleSuggestionClick(s.label)}
                style={{
                  cursor: loading ? 'not-allowed' : 'pointer', padding: '5px 12px',
                  borderRadius: 14, fontSize: 12,
                  background: 'rgba(34, 211, 240, 0.07)',
                  border: '1px solid rgba(34, 211, 240, 0.15)',
                  color: '#94a3b8', transition: 'all 0.3s ease',
                  opacity: loading ? 0.5 : 1,
                }}
              >
                {s.icon} {s.label}
              </Tag>
            ))}
          </div>
        </div>
      )}

      {/* ===== 消息列表 ===== */}
      <div style={{ maxHeight: 260, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
        {chatMessages.length === 0 && !comparison ? (
          <div style={{ textAlign: 'center', padding: '24px 0' }}>
            <div style={{ fontSize: 13, color: '#64748b' }}>告诉AI您想如何调整行程</div>
          </div>
        ) : (
          chatMessages.map((item, index) => (
            <div key={index} style={{
              padding: '10px 14px', borderRadius: 10,
              background: item.role === 'user' ? 'rgba(34,211,240,0.07)' : 'rgba(15,23,42,0.4)',
              border: `1px solid ${item.role === 'user' ? 'rgba(34,211,240,0.12)' : 'rgba(34,211,240,0.05)'}`,
            }}>
              <div style={{ fontSize: 10, color: '#64748b', marginBottom: 4, display: 'flex', justifyContent: 'space-between' }}>
                <span>{item.role === 'user' ? '🧑 您' : '🤖 AI助手'}</span>
                <span>{item.timestamp}</span>
              </div>
              <div style={{ fontSize: 13, color: '#e2e8f0', lineHeight: 1.5 }}>
                {item.loading ? (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: '#22d3f0' }}>
                    <LoadingOutlined spin />
                    {item.content}
                  </span>
                ) : item.content}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* ===== 输入区 ===== */}
      {!comparison && (
        <div style={{ display: 'flex', gap: 8 }}>
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onPressEnter={submit}
            placeholder="输入调整需求..."
            disabled={!plan || loading}
            style={{
              flex: 1, background: 'rgba(30, 41, 59, 0.5)',
              border: '1px solid rgba(34, 211, 240, 0.15)', borderRadius: 10,
              color: '#e2e8f0', height: 40,
            }}
          />
          <Button onClick={submit} loading={loading} disabled={!plan || !input.trim()}
            icon={!loading ? <SendOutlined /> : undefined}
            style={{
              height: 40, width: 40, borderRadius: 10, flexShrink: 0,
              background: input.trim() && !loading ? 'linear-gradient(135deg, #22d3f0, #06b6d4)' : 'rgba(34,211,240,0.1)',
              border: 'none', color: input.trim() && !loading ? '#060b14' : '#64748b',
            }}
          />
        </div>
      )}
    </div>
  )
}
