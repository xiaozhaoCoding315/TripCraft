import { Card, Empty, Segmented, Spin, Tag } from 'antd'
import { useEffect, useMemo, useRef, useState } from 'react'
import AMapLoader from '@amap/amap-jsapi-loader'
import type { ItineraryItem, TravelPlan } from '../types/travel'
import { EnvironmentOutlined, LoadingOutlined } from '@ant-design/icons'

interface MarkerItem extends ItineraryItem {
  day: number
  dateLabel: string  // "6/15" 格式的日期标签
}

export default function MapPanel({ plan }: { plan?: TravelPlan }) {
  const [day, setDay] = useState<string>('all')
  const [mapError, setMapError] = useState<string>()
  const [mapLoading, setMapLoading] = useState(false)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<any>(null)
  const overlaysRef = useRef<any[]>([])

  const allMarkers = useMemo<MarkerItem[]>(() => {
    const days = plan?.days || []
    return days.flatMap((item) => {
      const dateLabel = item.date
        ? item.date.slice(5).replace('-', '/')      // "2026-07-15" → "07/15"
        : `D${item.day}`
      return item.items.map((poi) => ({ ...poi, day: item.day, dateLabel }))
    }).filter((item) => item.location?.lng && item.location?.lat)
  }, [plan])

  const markers = useMemo<MarkerItem[]>(() => {
    return day === 'all'
      ? allMarkers
      : allMarkers.filter((item) => String(item.day) === day)
  }, [allMarkers, day])

  const totalWithCoords = allMarkers.length
  const totalItems = plan?.days.reduce((sum, d) => sum + d.items.length, 0) || 0

  useEffect(() => {
    const key = import.meta.env.VITE_AMAP_WEB_JS_KEY
    if (!plan || !containerRef.current || !key || markers.length === 0) return
    let disposed = false

    async function renderMap() {
      try {
        setMapLoading(true)
        const AMap = await AMapLoader.load({
          key,
          version: '2.0',
          plugins: ['AMap.Scale', 'AMap.ToolBar'],
        })
        if (disposed || !containerRef.current) return
        if (!mapRef.current) {
          mapRef.current = new AMap.Map(containerRef.current, {
            zoom: 12,
            viewMode: '2D',
            mapStyle: 'amap://styles/darkblue',
          })
          mapRef.current.addControl(new AMap.Scale())
          mapRef.current.addControl(new AMap.ToolBar())
        }
        overlaysRef.current.forEach((overlay) => mapRef.current.remove(overlay))
        overlaysRef.current = []
        const path = markers.map((item) => [item.location!.lng, item.location!.lat])
        markers.forEach((item) => {
          const typeEmoji: Record<string, string> = { transport:'🚄', attraction:'🎡', meal:'🍜', hotel:'🏨', rest:'☕', note:'📌' }
          const typeName: Record<string, string> = { transport:'交通', attraction:'景点', meal:'餐饮', hotel:'住宿', rest:'休息', note:'备注' }
          const emoji = typeEmoji[item.type] || '📍'
          const shortName = item.title.length > 10 ? item.title.slice(0, 8) + '…' : item.title
          const marker = new AMap.Marker({
            position: [item.location!.lng, item.location!.lat],
            title: item.title,
            label: { content: `${emoji}${item.dateLabel} ${shortName}`, direction: 'top' },
          })
          const info = new AMap.InfoWindow({
            content: `<div style="color:#111;max-width:280px;font-size:13px">
              <strong>${emoji} ${item.title}</strong><br/>
              <span style="color:#666">${item.description?.slice(0,80) || ''}</span><br/>
              <div style="margin-top:4px;font-size:11px;color:#888">
                🕐 ${item.time} | ${typeName[item.type] || item.type}
                ${item.cost ? ` | ¥${item.cost}` : ''}<br/>
                📍 ${item.location?.address || '地址未标注'}
              </div>
            </div>`,
            offset: new AMap.Pixel(0, -30),
          })
          marker.on('click', () => info.open(mapRef.current, marker.getPosition()))
          mapRef.current.add(marker)
          overlaysRef.current.push(marker)
        })
        if (path.length > 1) {
          const polyline = new AMap.Polyline({
            path,
            strokeColor: '#36d399',
            strokeWeight: 5,
            strokeOpacity: 0.9,
            lineJoin: 'round',
          })
          mapRef.current.add(polyline)
          overlaysRef.current.push(polyline)
        }
        mapRef.current.setFitView(overlaysRef.current)
        setMapError(undefined)
      } catch (error) {
        setMapError(error instanceof Error ? error.message : '高德地图加载失败')
      } finally {
        setMapLoading(false)
      }
    }

    renderMap()
    return () => {
      disposed = true
      // 清理所有覆盖物
      if (mapRef.current) {
        overlaysRef.current.forEach(o => {
          try { mapRef.current.remove(o) } catch {}
        })
        overlaysRef.current = []
        try { mapRef.current.destroy() } catch {}
        mapRef.current = null
      }
    }
  }, [plan, markers])

  return (
    <Card
      title={
        <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <EnvironmentOutlined style={{ color: 'var(--accent-primary)' }} />
          高德地图路线可视化
          {totalWithCoords > 0 && (
            <Tag
              style={{
                fontSize: '11px',
                background: 'rgba(104, 211, 145, 0.15)',
                borderColor: 'rgba(104, 211, 145, 0.3)',
                color: 'var(--status-success)',
              }}
            >
              {totalWithCoords}/{totalItems} 个定位点
            </Tag>
          )}
        </span>
      }
      className="glass-card map-panel"
      style={{ borderColor: 'var(--surface-border)' }}
    >
      {!plan ? (
        <Empty description="行程生成后显示地图路线" />
      ) : (
        <>
          <Segmented
            value={day}
            onChange={(value) => setDay(String(value))}
            options={[
              { label: '全部', value: 'all' },
              ...plan.days.map((item) => {
                const label = item.date
                  ? item.date.slice(5).replace('-', '/')
                  : `D${item.day}`
                return { label, value: String(item.day) }
              }),
            ]}
            style={{ marginBottom: '12px' }}
          />

          {!import.meta.env.VITE_AMAP_WEB_JS_KEY ? (
            <div
              className="map-placeholder"
              style={{
                background: `
                  linear-gradient(rgba(99, 179, 237, 0.05) 1px, transparent 1px),
                  linear-gradient(90deg, rgba(99, 179, 237, 0.05) 1px, transparent 1px),
                  rgba(18, 24, 41, 0.9)
                `,
                border: '1px dashed rgba(99, 179, 237, 0.3)',
                borderRadius: '16px',
                padding: '48px 24px',
                textAlign: 'center',
              }}
            >
              <div>
                <h3 style={{ color: 'var(--text-primary)' }}>
                  <EnvironmentOutlined style={{ marginRight: '8px', color: 'var(--accent-primary)' }} />
                  配置地图 API Key
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
                  请在 <code>.env</code> 中设置 <code>VITE_AMAP_WEB_JS_KEY</code> 启用高德地图。
                </p>
              </div>
            </div>
          ) : allMarkers.length === 0 ? (
            <div
              className="map-placeholder"
              style={{
                background: `
                  linear-gradient(rgba(99, 179, 237, 0.05) 1px, transparent 1px),
                  linear-gradient(90deg, rgba(99, 179, 237, 0.05) 1px, transparent 1px),
                  rgba(18, 24, 41, 0.9)
                `,
                border: '1px dashed rgba(99, 179, 237, 0.3)',
                borderRadius: '16px',
                padding: '48px 24px',
                textAlign: 'center',
              }}
            >
              <div>
                <h3 style={{ color: 'var(--text-primary)' }}>
                  <EnvironmentOutlined style={{ marginRight: '8px', color: 'var(--accent-primary)' }} />
                  正在获取坐标数据
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
                  当前行程数据正在后台获取地理坐标，请稍候刷新页面查看。
                </p>
                <p style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                  如果持续无数据，可能是高德 API Key 未配置或地址解析失败。
                </p>
              </div>
            </div>
          ) : (
            <>
              {mapLoading && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    padding: '12px',
                    color: 'var(--text-muted)',
                    fontSize: '13px',
                  }}
                >
                  <LoadingOutlined spin /> 地图加载中...
                </div>
              )}
              <div
                ref={containerRef}
                className="amap-container"
                style={{
                  border: '1px solid rgba(99, 179, 237, 0.3)',
                  borderRadius: '16px',
                  overflow: 'hidden',
                  minHeight: '400px',
                  height: 'calc(100vh - 400px)',
                  maxHeight: '600px',
                }}
              />
              {mapError && (
                <p className="error-box" style={{ marginTop: '12px' }}>
                  {mapError}
                </p>
              )}
              {/* 类型图例 + 标记速览 */}
              <div style={{ marginTop: 14 }}>
                {/* 图例 */}
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 10 }}>
                  {[
                    { emoji: '🎡', label: '景点', color: '#4ade80' },
                    { emoji: '🏨', label: '住宿', color: '#a78bfa' },
                    { emoji: '🍜', label: '餐饮', color: '#fbbf24' },
                    { emoji: '🚄', label: '交通', color: '#2dd4bf' },
                    { emoji: '☕', label: '休息', color: '#22d3f0' },
                  ].map(t => (
                    <span key={t.label} style={{ fontSize: 11, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 3 }}>
                      <span style={{ width: 6, height: 6, borderRadius: '50%', background: t.color, boxShadow: `0 0 4px ${t.color}` }} />
                      {t.emoji} {t.label}
                    </span>
                  ))}
                  <span style={{ fontSize: 11, color: '#64748b', marginLeft: 4 }}>
                    💡 点击地图标记查看详情
                  </span>
                </div>
                {/* 标记列表 */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {markers.slice(0, 14).map((m) => {
                    const emojiMap: Record<string, string> = { transport:'🚄', attraction:'🎡', meal:'🍜', hotel:'🏨', rest:'☕', note:'📌' }
                    return (
                      <Tag key={m.id} style={{
                        fontSize: 11, cursor: 'pointer',
                        background: 'rgba(34,211,240,0.08)',
                        borderColor: 'rgba(34,211,240,0.18)',
                        color: '#94a3b8',
                        borderRadius: 14,
                      }}>
                        {(emojiMap[m.type] || '📍')} {m.dateLabel} {m.title.slice(0, 8)}
                      </Tag>
                    )
                  })}
                </div>
              </div>
            </>
          )}
        </>
      )}
    </Card>
  );
}
