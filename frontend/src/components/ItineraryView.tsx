import { BankOutlined, CarOutlined, CoffeeOutlined, EnvironmentOutlined, HomeOutlined, RestOutlined, WalletOutlined } from '@ant-design/icons'
import { Card, Collapse, Empty, Progress, Space, Statistic, Tag, Timeline, Typography } from 'antd'
import type { ItineraryItem, TravelPlan } from '../types/travel'

const iconMap: Record<ItineraryItem['type'], React.ReactNode> = {
  transport: <CarOutlined style={{ color: '#4fd1c5' }} />,
  attraction: <EnvironmentOutlined style={{ color: '#68d391' }} />,
  meal: <CoffeeOutlined style={{ color: '#f6ad55' }} />,
  hotel: <HomeOutlined style={{ color: '#9f7aea' }} />,
  rest: <RestOutlined style={{ color: '#63b3ed' }} />,
  note: <BankOutlined style={{ color: '#fc8181' }} />,
}

const typeColors: Record<ItineraryItem['type'], string> = {
  transport: '#4fd1c5',
  attraction: '#68d391',
  meal: '#f6ad55',
  hotel: '#9f7aea',
  rest: '#63b3ed',
  note: '#fc8181',
};

const typeLabels: Record<ItineraryItem['type'], string> = {
  transport: '交通',
  attraction: '景点',
  meal: '餐饮',
  hotel: '住宿',
  rest: '休息',
  note: '备注',
};

export default function ItineraryView({ plan }: { plan?: TravelPlan }) {
  if (!plan) {
    return <Empty className="empty-panel" description="暂无行程，先创建一次旅行规划" />
  }

  // Calculate cost breakdown by type
  const costByType = plan.days.reduce((acc, day) => {
    day.items.forEach(item => {
      if (item.cost && item.cost > 0) {
        acc[item.type] = (acc[item.type] || 0) + item.cost
      }
    })
    return acc
  }, {} as Record<string, number>)

  const totalCost = plan.total_estimated_cost || Object.values(costByType).reduce((a, b) => a + b, 0)

  return (
    <div className="itinerary-view">
      {/* Summary Card */}
      <div className="summary-card card">
        <div className="summary-header">
          <div className="summary-title">
            <span className="summary-icon" style={{ background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))' }}>
              <WalletOutlined style={{ color: 'white', fontSize: 16 }} />
            </span>
            <div>
              <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>
                {plan.destination} 行程概览
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {(plan as any).departure_city ? `从 ${(plan as any).departure_city} 出发` : '旅行计划'}
              </div>
            </div>
          </div>
          <div className="summary-stats">
            <div className="stat-item">
              <div className="stat-value" style={{ color: 'var(--accent-primary)' }}>{plan.days.length}</div>
              <div className="stat-label">天</div>
            </div>
            <div className="stat-item">
              <div className="stat-value" style={{ color: 'var(--status-success)' }}>
                ¥{(plan.total_estimated_cost || 0).toLocaleString()}
              </div>
              <div className="stat-label">预计费用</div>
            </div>
          </div>
        </div>

        {/* Cost Breakdown Bar */}
        {totalCost > 0 && (
          <div style={{ marginTop: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>费用构成</span>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>¥{totalCost.toLocaleString()}</span>
            </div>
            <div style={{ display: 'flex', height: '8px', borderRadius: '4px', overflow: 'hidden', gap: '2px' }}>
              {Object.entries(costByType).map(([type, cost]) => (
                <div
                  key={type}
                  style={{
                    width: `${(cost / totalCost) * 100}%`,
                    background: typeColors[type as keyof typeof typeColors] || '#63b3ed',
                    transition: 'width 0.5s ease',
                  }}
                  title={`${typeLabels[type as keyof typeof typeLabels] || type}: ¥${cost}`}
                />
              ))}
            </div>
            <div style={{ display: 'flex', gap: '16px', marginTop: '8px', flexWrap: 'wrap' }}>
              {Object.entries(costByType).map(([type, cost]) => (
                <div key={type} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <div style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    background: typeColors[type as keyof typeof typeColors] || '#63b3ed',
                  }} />
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    {typeLabels[type as keyof typeof typeLabels] || type} ¥{cost}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Itinerary Days */}
      <Collapse
        defaultActiveKey={plan.days.map((day) => String(day.day))}
        style={{
          background: 'transparent',
          border: 'none',
        }}
        items={plan.days.map((day, dayIndex) => {
          // Calculate day cost
          const dayCost = day.items.reduce((sum, item) => sum + (item.cost || 0), 0)

          return {
            key: String(day.day),
            label: (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '4px 0',
              }}>
                <Space wrap>
                  <strong style={{ color: 'var(--text-primary)' }}>
                    Day {day.day}: {day.title}
                  </strong>
                  <Tag color={day.pace === 'relaxed' ? 'green' : 'blue'}>
                    {day.pace === 'relaxed' ? '轻松' : '紧凑'}
                  </Tag>
                  {day.date && <Tag>{day.date}</Tag>}
                  {day.weather_summary && (
                    <span className="muted">{day.weather_summary}</span>
                  )}
                </Space>
                {dayCost > 0 && (
                  <Tag
                    color="gold"
                    style={{
                      background: 'rgba(246, 173, 85, 0.15)',
                      borderColor: 'rgba(246, 173, 85, 0.3)',
                      color: '#f6ad55',
                    }}
                  >
                    ¥{dayCost.toLocaleString()}
                  </Tag>
                )}
              </div>
            ),
            children: (
              <Timeline
                style={{ paddingTop: '8px' }}
                items={day.items.map((item, itemIndex) => ({
                  dot: (
                    <div style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: '50%',
                      background: `${typeColors[item.type]}22`,
                      border: `2px solid ${typeColors[item.type]}`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      marginLeft: '-8px',
                    }}>
                      {iconMap[item.type]}
                    </div>
                  ),
                  children: (
                    <div
                      className="plan-item"
                      id={item.id}
                      style={{
                        animation: `slideInRight 0.3s ease ${itemIndex * 0.1}s both`,
                        padding: '12px',
                        borderRadius: '12px',
                        background: 'rgba(18, 24, 41, 0.5)',
                        border: '1px solid var(--surface-border)',
                        marginBottom: '8px',
                        transition: 'all 0.3s ease',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = typeColors[item.type]
                        e.currentTarget.style.transform = 'translateX(4px)'
                        e.currentTarget.style.background = 'rgba(18, 24, 41, 0.8)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = 'var(--surface-border)'
                        e.currentTarget.style.transform = 'translateX(0)'
                        e.currentTarget.style.background = 'rgba(18, 24, 41, 0.5)'
                      }}
                    >
                      <div className="plan-item-head" style={{ marginBottom: '8px' }}>
                        <Typography.Text strong style={{ color: 'var(--text-primary)' }}>
                          {item.time} · {item.title}
                        </Typography.Text>
                        {item.cost != null && item.cost > 0 && (
                          <Tag
                            color="gold"
                            style={{
                              background: 'rgba(246, 173, 85, 0.15)',
                              borderColor: 'rgba(246, 173, 85, 0.3)',
                              color: '#f6ad55',
                            }}
                          >
                            ¥{item.cost}
                          </Tag>
                        )}
                      </div>
                      <Typography.Paragraph style={{ color: 'var(--text-secondary)', marginBottom: '8px' }}>
                        {item.description}
                      </Typography.Paragraph>
                      {item.location?.address && (
                        <div className="muted" style={{ fontSize: '12px', marginBottom: '4px' }}>
                          📍 {item.location.address}
                        </div>
                      )}
                      <Space wrap size={4}>
                        {item.source_refs.map((source, idx) => (
                          <Tag
                            key={`${item.id}-${idx}`}
                            style={{
                              fontSize: '11px',
                              padding: '2px 8px',
                              background: 'rgba(99, 179, 237, 0.1)',
                              borderColor: 'rgba(99, 179, 237, 0.2)',
                              color: 'var(--accent-primary)',
                            }}
                          >
                            {source.label}
                          </Tag>
                        ))}
                      </Space>
                    </div>
                  ),
                }))}
              />
            ),
          }
        })}
      />
    </div>
  )
}
