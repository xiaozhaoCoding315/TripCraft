import type { TripCraftPlugin, PluginContext } from '../types'

/**
 * 快速参考插件 — 显示目的地实用信息
 */
export const QuickFactsPlugin: TripCraftPlugin = {
  meta: {
    id: 'quick-facts',
    name: '实用速查',
    version: '1.0.0',
    description: '显示目的地天气、汇率、时区等实用信息',
    icon: '📊',
    slot: 'sidebar',
  },

  render: (ctx: PluginContext) => {
    if (!ctx.plan) return null
    const days = ctx.plan.days.length
    const cost = ctx.plan.total_estimated_cost || 0
    const avgPerDay = days > 0 ? Math.round(cost / days) : 0

    return (
      <div key="quick-facts" style={{
        padding: 12, borderRadius: 10, marginBottom: 8,
        background: 'rgba(15,23,42,0.5)', border: '1px solid rgba(34,211,240,0.1)',
        fontSize: 12,
      }}>
        <div style={{ color: '#94a3b8', fontWeight: 600, marginBottom: 8 }}>📊 实用速查</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#64748b' }}>目的地</span>
            <span style={{ color: '#e2e8f0' }}>{ctx.plan.destination}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#64748b' }}>天数</span>
            <span style={{ color: '#e2e8f0' }}>{days}天</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#64748b' }}>人均/天</span>
            <span style={{ color: '#22d3f0' }}>≈¥{avgPerDay.toLocaleString()}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#64748b' }}>版本</span>
            <span style={{ color: '#a78bfa' }}>v{ctx.plan.version}</span>
          </div>
        </div>
      </div>
    )
  },
}
