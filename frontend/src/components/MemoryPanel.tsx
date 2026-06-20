/**
 * MemoryPanel v2 - Historical plans + user memory sidebar
 * Enhanced with neon styling
 */

import { DeleteOutlined, ReloadOutlined } from '@ant-design/icons'
import { Button, Empty, List, Tag, Tooltip, message } from 'antd'
import { motion } from 'framer-motion'
import { travelAPI } from '../api/client'
import type { MemoryItem, PlanSummary } from '../types/travel'

interface Props {
  plans: PlanSummary[]
  memory: MemoryItem[]
  onReload: () => Promise<void>
  onLoadPlan: (planId: string) => Promise<void>
  onDeletePlan: (planId: string) => Promise<void>
  currentPlanId: string | null
}

const categoryLabels: Record<string, { label: string; color: string }> = {
  pace: { label: '节奏', color: '#22d3f0' },
  budget: { label: '预算', color: '#fbbf24' },
  traveler: { label: '出行人', color: '#4ade80' },
  interest: { label: '兴趣', color: '#a78bfa' },
  hotel: { label: '住宿', color: '#2dd4bf' },
  avoid: { label: '避开', color: '#fb7185' },
  transport: { label: '交通', color: '#f59e0b' },
  food: { label: '美食', color: '#f472b6' },
}

export default function MemoryPanel({
  plans,
  memory,
  onReload,
  onLoadPlan,
  onDeletePlan,
  currentPlanId,
}: Props) {
  async function deleteMemory(key: string) {
    try {
      await travelAPI.deleteMemory(key)
      message.success('记忆已删除')
      await onReload()
    } catch {
      message.error('删除记忆失败')
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      {/* Historical Plans */}
      <div>
        <div style={{
          fontSize: 13,
          color: 'var(--text-muted)',
          marginBottom: 10,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
        }}>
          <span>📋 历史行程 ({plans.length})</span>
          <Button
            type="text"
            size="small"
            icon={<ReloadOutlined />}
            onClick={onReload}
            style={{ color: 'var(--text-muted)', fontSize: 11 }}
          >
            刷新
          </Button>
        </div>
        {plans.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={<span style={{ color: '#64748b' }}>暂无历史行程</span>}
            style={{ padding: '16px 0' }}
          />
        ) : (
          <List
            size="small"
            dataSource={plans.slice(0, 10)}
            renderItem={(plan) => {
              const isActive = currentPlanId === plan.plan_id
              return (
                <List.Item
                  onClick={() => onLoadPlan(plan.plan_id)}
                  style={{
                    padding: '10px 12px',
                    borderRadius: 10,
                    marginBottom: 4,
                    background: isActive
                      ? 'rgba(34, 211, 240, 0.12)'
                      : 'rgba(15, 23, 42, 0.5)',
                    border: isActive
                      ? '1px solid rgba(34, 211, 240, 0.4)'
                      : '1px solid rgba(34, 211, 240, 0.08)',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.borderColor = 'rgba(34,211,240,0.25)'
                      e.currentTarget.style.background = 'rgba(34,211,240,0.05)'
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.borderColor = 'rgba(34,211,240,0.08)'
                      e.currentTarget.style.background = 'rgba(15,23,42,0.5)'
                    }
                  }}
                  actions={[
                    <Button
                      key="load"
                      type="link"
                      size="small"
                      onClick={(e) => { e.stopPropagation(); onLoadPlan(plan.plan_id) }}
                      style={{ color: '#22d3f0', fontSize: 12 }}
                    >
                      查看
                    </Button>,
                    <Button
                      key="delete"
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={(e) => { e.stopPropagation(); onDeletePlan(plan.plan_id) }}
                    />,
                  ]}
                >
                  <List.Item.Meta
                    title={
                      <div style={{ display: 'flex', alignItems: 'center', gap: 5, flexWrap: 'nowrap' }}>
                        {plan.departure_city ? (
                          <span style={{
                            color: '#e2e8f0', fontSize: 12, fontWeight: 500,
                            overflow: 'hidden', whiteSpace: 'nowrap',
                            flex: '1 1 auto', minWidth: 0,
                            display: 'flex', alignItems: 'center', gap: 0,
                          }} title={`${plan.departure_city} → ${plan.destination}`}>
                            <span style={{
                              color: '#64748b', fontWeight: 400,
                              maxWidth: 70, overflow: 'hidden', textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap', flexShrink: 1,
                            }}>{plan.departure_city}</span>
                            <span style={{ color: '#22d3f0', margin: '0 4px', flexShrink: 0 }}>→</span>
                            <span style={{ flexShrink: 0 }}>{plan.destination}</span>
                          </span>
                        ) : (
                          <span style={{
                            color: '#e2e8f0', fontSize: 12, fontWeight: 500,
                            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                            flex: '1 1 auto', minWidth: 0,
                          }}>
                            📍 {plan.destination}
                          </span>
                        )}
                        {isActive && (
                          <Tag style={{ fontSize: 9, flexShrink: 0, background: 'rgba(34,211,240,0.2)', borderColor: 'rgba(34,211,240,0.4)', color: '#22d3f0', padding: '0 6px', lineHeight: '16px' }}>
                            当前
                          </Tag>
                        )}
                      </div>
                    }
                    description={
                      <span style={{ fontSize: 11, color: '#64748b' }}>
                        {plan.days}天 · ¥{Math.round(plan.total_estimated_cost || 0).toLocaleString()}
                      </span>
                    }
                  />
                </List.Item>
              )
            }}
          />
        )}
      </div>

      {/* Memory Items */}
      <div>
        <div style={{
          fontSize: 13,
          color: 'var(--text-muted)',
          marginBottom: 10,
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.5px',
        }}>
          🧠 用户偏好记忆 ({memory.length})
        </div>
        {memory.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={<span style={{ color: '#64748b' }}>AI会从对话中学习偏好</span>}
            style={{ padding: '16px 0' }}
          />
        ) : (
          <List
            size="small"
            dataSource={memory}
            renderItem={(item) => {
              const category = categoryLabels[item.category] || { label: item.category, color: '#64748b' }
              return (
                <List.Item
                  style={{
                    padding: '8px 12px',
                    borderRadius: 8,
                    marginBottom: 4,
                    background: 'rgba(15, 23, 42, 0.4)',
                    border: '1px solid rgba(34,211,240,0.06)',
                  }}
                  actions={[
                    <Tooltip key="delete" title="删除此记忆">
                      <Button
                        type="text"
                        size="small"
                        icon={<DeleteOutlined />}
                        onClick={() => deleteMemory(item.key)}
                        style={{ color: '#64748b' }}
                      />
                    </Tooltip>,
                  ]}
                >
                  <List.Item.Meta
                    title={
                      <span
                        style={{
                          color: '#cbd5e1',
                          fontSize: 12,
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical',
                          overflow: 'hidden',
                          wordBreak: 'break-word',
                        }}
                        title={item.value}
                      >
                        {item.value}
                      </span>
                    }
                    description={
                      <Tag
                        style={{
                          fontSize: 10,
                          margin: 0,
                          marginTop: 4,
                          background: `${category.color}20`,
                          borderColor: `${category.color}40`,
                          color: category.color,
                          flexShrink: 0,
                        }}
                      >
                        {category.label}
                      </Tag>
                    }
                  />
                </List.Item>
              )
            }}
          />
        )}
      </div>
    </div>
  )
}
