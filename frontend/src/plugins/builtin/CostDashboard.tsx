import type { TripCraftPlugin, PluginContext } from '../types'
import { motion } from 'framer-motion'

const TYPE_CONFIG: Record<string, { emoji: string; label: string; color: string }> = {
  transport:   { emoji: '🚄', label: '交通', color: '#2dd4bf' },
  attraction:  { emoji: '🎡', label: '景点', color: '#4ade80' },
  meal:        { emoji: '🍜', label: '餐饮', color: '#fbbf24' },
  hotel:       { emoji: '🏨', label: '住宿', color: '#a78bfa' },
  rest:        { emoji: '☕', label: '休息', color: '#22d3f0' },
  note:        { emoji: '📌', label: '备注', color: '#fb7185' },
}

export const CostDashboardPlugin: TripCraftPlugin = {
  meta: {
    id: 'cost-dashboard',
    name: '费用仪表盘',
    version: '1.0.0',
    description: '可视化展示行程费用分布',
    icon: '📊',
    slot: 'sidebar',
  },

  render: (ctx: PluginContext) => {
    if (!ctx.plan) return null

    // 按类型汇总费用
    const costByType: Record<string, number> = {}
    ctx.plan.days.forEach(day => {
      day.items.forEach(item => {
        if (item.cost && item.cost > 0) {
          costByType[item.type] = (costByType[item.type] || 0) + item.cost
        }
      })
    })

    const totalCost = ctx.plan.total_estimated_cost
      || Object.values(costByType).reduce((s, c) => s + c, 0)

    // 按天汇总
    const dailyCosts = ctx.plan.days.map(d => ({
      day: d.day,
      cost: d.estimated_cost || d.items.reduce((s, i) => s + (i.cost || 0), 0),
    }))
    const maxDaily = Math.max(...dailyCosts.map(d => d.cost), 1)

    const entries = Object.entries(costByType).sort((a, b) => b[1] - a[1])

    if (totalCost === 0) return null

    return (
      <div key="cost-dashboard" style={{
        padding: 12, borderRadius: 10, marginBottom: 8,
        background: 'rgba(15,23,42,0.5)', border: '1px solid rgba(34,211,240,0.1)',
        fontSize: 11,
      }}>
        <div style={{ color: '#94a3b8', fontWeight: 600, marginBottom: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>📊 费用仪表盘</span>
          <motion.span
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            style={{ color: '#4ade80', fontWeight: 700, fontSize: 13 }}
          >
            ¥{totalCost.toLocaleString()}
          </motion.span>
        </div>

        {/* 按类型柱状图 */}
        <div style={{ marginBottom: 14 }}>
          <div style={{ color: '#64748b', fontSize: 10, marginBottom: 6 }}>按类型分布</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            {entries.map(([type, cost]) => {
              const cfg = TYPE_CONFIG[type] || { emoji: '📌', label: type, color: '#64748b' }
              const pct = Math.round((cost / totalCost) * 100)
              return (
                <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ flexShrink: 0, fontSize: 12 }}>{cfg.emoji}</span>
                  <span style={{ width: 28, flexShrink: 0, color: '#94a3b8', fontSize: 10 }}>{cfg.label}</span>
                  <div style={{ flex: 1, height: 14, background: 'rgba(0,0,0,0.3)', borderRadius: 4, overflow: 'hidden' }}>
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ duration: 0.8, ease: 'easeOut', delay: 0.1 }}
                      style={{
                        height: '100%', borderRadius: 4,
                        background: `linear-gradient(90deg, ${cfg.color}cc, ${cfg.color})`,
                        boxShadow: `0 0 6px ${cfg.color}40`,
                        minWidth: pct > 0 ? 4 : 0,
                      }}
                    />
                  </div>
                  <span style={{ width: 52, flexShrink: 0, textAlign: 'right', color: '#e2e8f0', fontSize: 10 }}>
                    ¥{cost.toLocaleString()}
                  </span>
                  <span style={{ width: 28, flexShrink: 0, textAlign: 'right', color: cfg.color, fontSize: 10, fontWeight: 600 }}>
                    {pct}%
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* 每日费用趋势 */}
        {dailyCosts.length > 1 && (
          <div>
            <div style={{ color: '#64748b', fontSize: 10, marginBottom: 6 }}>每日费用趋势</div>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 60, paddingTop: 4 }}>
              {dailyCosts.map(d => {
                const h = Math.max((d.cost / maxDaily) * 56, 4)
                return (
                  <div key={d.day} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
                    <span style={{ color: '#e2e8f0', fontSize: 9, fontWeight: 500 }}>
                      ¥{(d.cost / 1000).toFixed(1)}k
                    </span>
                    <motion.div
                      initial={{ height: 0 }}
                      animate={{ height: h }}
                      transition={{ duration: 0.6, ease: 'easeOut', delay: 0.2 + d.day * 0.1 }}
                      style={{
                        width: '100%', maxWidth: 32, borderRadius: '4px 4px 0 0',
                        background: `linear-gradient(to top, #22d3f0, #a78bfa)`,
                        boxShadow: '0 0 8px rgba(34,211,240,0.3)',
                      }}
                    />
                    <span style={{ color: '#64748b', fontSize: 9 }}>D{d.day}</span>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    )
  },
}
