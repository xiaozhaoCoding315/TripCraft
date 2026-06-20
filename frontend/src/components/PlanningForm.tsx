import { Button, Card, DatePicker, Form, Input, InputNumber, Select, Space, Tag } from 'antd'
import dayjs from 'dayjs'
import type { TravelPlanRequest } from '../types/travel'
import { RocketOutlined, PlusOutlined } from '@ant-design/icons'
import { useState } from 'react'

interface Props {
  loading: boolean
  onSubmit: (request: TravelPlanRequest) => void
}

// 可选偏好标签
const PRESET_PREFS = [
  { key: 'nature', label: '🏔️ 自然风光', value: '喜欢自然风光' },
  { key: 'culture', label: '🏛️ 历史文化', value: '喜欢历史人文景点' },
  { key: 'food', label: '🍜 美食探店', value: '重视当地美食体验' },
  { key: 'photo', label: '📸 拍照打卡', value: '偏好适合拍照的地点' },
  { key: 'shopping', label: '🛍️ 购物', value: '喜欢购物和商业区' },
  { key: 'relax', label: '🧘 轻松慢游', value: '节奏不要太快，多休息' },
  { key: 'metro', label: '🚇 近地铁', value: '酒店靠近地铁站' },
  { key: 'family', label: '👨‍👩‍👧 亲子友好', value: '适合带孩子的景点和酒店' },
  { key: 'luxury', label: '✨ 高品质', value: '偏好高档酒店和餐厅' },
  { key: 'budget', label: '💰 经济实惠', value: '控制预算，性价比优先' },
]

export default function PlanningForm({ loading, onSubmit }: Props) {
  const [customPref, setCustomPref] = useState('')
  const [selectedPrefs, setSelectedPrefs] = useState<string[]>(['nature', 'culture'])
  const [customPrefs, setCustomPrefs] = useState<string[]>([])

  function togglePref(key: string) {
    setSelectedPrefs(prev =>
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    )
  }

  function addCustomPref() {
    if (!customPref.trim()) return
    setCustomPrefs(prev => [...prev, customPref.trim()])
    setCustomPref('')
  }

  function buildPreferences(): string {
    const selected = PRESET_PREFS
      .filter(p => selectedPrefs.includes(p.key))
      .map(p => p.value)
    const all = [...selected, ...customPrefs]
    return all.join('；')
  }

  return (
    <Card
      title={
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <RocketOutlined style={{ color: 'var(--accent-primary)' }} />
          创建旅行规划
        </span>
      }
      className="glass-card"
      style={{ borderColor: 'var(--surface-border)', transition: 'all 0.3s ease' }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = 'var(--surface-border-hover)'
        e.currentTarget.style.boxShadow = 'var(--glow-subtle), var(--shadow-lg)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = 'var(--surface-border)'
        e.currentTarget.style.boxShadow = 'var(--shadow-lg)'
      }}
    >
      <Form
        layout="vertical"
        initialValues={{
          destination: '杭州',
          departure_city: '上海',
          start_date: dayjs().add(14, 'day'),
          days: 3,
          budget: 5000,
          adults: 2,
          children: 0,
          seniors: 0,
          interests: ['自然风光', '博物馆'],
        }}
        onFinish={(values) => {
          const prefs = buildPreferences()
          onSubmit({
            destination: values.destination,
            departure_city: values.departure_city,
            start_date: values.start_date.format('YYYY-MM-DD'),
            days: values.days,
            budget: values.budget,
            travelers: {
              adults: values.adults,
              children: values.children,
              seniors: values.seniors,
              mobility_notes: values.mobility_notes || '',
            },
            interests: values.interests || [],
            preferences: prefs || undefined,
          })
        }}
      >
        <Space.Compact block>
          <Form.Item name="departure_city" label="出发地" style={{ width: '45%' }}>
            <Input placeholder="上海" />
          </Form.Item>
          <Form.Item name="destination" label="目的地" rules={[{ required: true }]} style={{ width: '55%' }}>
            <Input placeholder="杭州" />
          </Form.Item>
        </Space.Compact>
        <Space.Compact block>
          <Form.Item name="start_date" label="出发日期" rules={[{ required: true }]} style={{ width: '50%' }}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="days" label="天数" rules={[{ required: true }]} style={{ width: '50%' }}>
            <InputNumber min={1} max={14} style={{ width: '100%' }} />
          </Form.Item>
        </Space.Compact>
        <Form.Item name="budget" label="总预算（元）">
          <InputNumber min={0} style={{ width: '100%' }} />
        </Form.Item>
        <Space.Compact block>
          <Form.Item name="adults" label="成人" style={{ width: '33%' }}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="children" label="儿童" style={{ width: '33%' }}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="seniors" label="老人" style={{ width: '34%' }}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
        </Space.Compact>
        <Form.Item name="mobility_notes" label="同行人特征 / 行动限制">
          <Input.TextArea rows={2} placeholder="如：父母60岁腿脚不便、带婴儿车（可选）" />
        </Form.Item>
        <Form.Item name="interests" label="兴趣偏好">
          <Select mode="tags" placeholder="输入并回车添加" options={['自然风光', '历史文化', '美食', '亲子', '购物', '摄影', '户外运动', '夜间生活'].map(v => ({ value: v }))} />
        </Form.Item>

        {/* ===== 自定义偏好标签 ===== */}
        <Form.Item label="出行偏好（可多选 + 自定义）" style={{ marginBottom: 4 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {PRESET_PREFS.map(p => {
              const active = selectedPrefs.includes(p.key)
              return (
                <Tag
                  key={p.key}
                  onClick={() => togglePref(p.key)}
                  style={{
                    cursor: 'pointer', padding: '4px 12px', borderRadius: 16,
                    fontSize: 12, border: active
                      ? '1px solid rgba(34,211,240,0.5)'
                      : '1px solid rgba(34,211,240,0.15)',
                    background: active ? 'rgba(34,211,240,0.15)' : 'rgba(15,23,42,0.4)',
                    color: active ? '#22d3f0' : '#94a3b8',
                    transition: 'all 0.2s ease',
                  }}
                >
                  {p.label}
                </Tag>
              )
            })}
          </div>
        </Form.Item>

        {/* 自定义偏好输入 */}
        <Form.Item style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <Input
              value={customPref}
              onChange={e => setCustomPref(e.target.value)}
              onPressEnter={addCustomPref}
              placeholder="输入自定义偏好，如：酒店要有泳池"
              style={{ flex: 1 }}
            />
            <Button
              onClick={addCustomPref}
              icon={<PlusOutlined />}
              disabled={!customPref.trim()}
              type="primary"
              style={{ borderRadius: 10 }}
            >
              添加
            </Button>
          </div>
          {customPrefs.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 8 }}>
              {customPrefs.map((p, i) => (
                <Tag key={i} closable onClose={() => setCustomPrefs(prev => prev.filter((_, j) => j !== i))}
                  style={{ fontSize: 11, background: 'rgba(167,139,250,0.1)', border: '1px solid rgba(167,139,250,0.2)', color: '#a78bfa', borderRadius: 12 }}
                >
                  {p}
                </Tag>
              ))}
            </div>
          )}
        </Form.Item>

        <Button
          type="primary" htmlType="submit" block size="large" loading={loading}
          icon={loading ? undefined : <RocketOutlined />}
          style={{
            height: 48, fontSize: 16, fontWeight: 600,
            background: loading ? undefined : 'linear-gradient(135deg, #22d3f0, #06b6d4)',
            border: 'none', boxShadow: 'var(--glow-cyan-medium)', borderRadius: 12,
            transition: 'all 0.3s ease',
          }}
        >
          {loading ? '规划中...' : '🚀 启动 Multi-Agent 规划'}
        </Button>
      </Form>
    </Card>
  )
}
