import type { TripCraftPlugin, PluginContext } from '../types'

/** 天气描述映射 */
const WEATHER_MAP: Record<string, { emoji: string; label: string }> = {
  '晴': { emoji: '☀️', label: '晴' }, '少云': { emoji: '🌤️', label: '少云' },
  '多云': { emoji: '⛅', label: '多云' }, '阴': { emoji: '☁️', label: '阴' },
  '小雨': { emoji: '🌧️', label: '小雨' }, '中雨': { emoji: '🌧️', label: '中雨' },
  '大雨': { emoji: '⛈️', label: '大雨' }, '阵雨': { emoji: '🌦️', label: '阵雨' },
  '雪': { emoji: '❄️', label: '雪' }, '雾': { emoji: '🌫️', label: '雾' },
}

function parseWeather(desc: string) {
  for (const [key, val] of Object.entries(WEATHER_MAP)) {
    if (desc.includes(key)) return val
  }
  return { emoji: '🌡️', label: desc.slice(0, 4) }
}

interface DayWeather { day: number; date: string; dayWeather: string; nightWeather: string; dayTemp: string; nightTemp: string; wind: string; power: string }

/** 从 raw_context 或 day items 中提取天气 */
function extractWeather(ctx: PluginContext): DayWeather[] {
  if (!ctx.plan) return []
  const raw = ctx.plan.raw_context || {}
  const weatherData = (raw.weather as any) || {}
  const casts: any[] = weatherData.casts || []
  const totalDays = ctx.plan.days.length

  return ctx.plan.days.map((d, i) => {
    // 优先从高德casts获取（前4天），超出则用plan内置的天气
    const cast = casts[i]
    if (cast) {
      return {
        day: d.day,
        date: cast.date || d.date || '',
        dayWeather: cast.dayweather || '--',
        nightWeather: cast.nightweather || '--',
        dayTemp: cast.daytemp || '--',
        nightTemp: cast.nighttemp || '--',
        wind: cast.daywind || cast.nightwind || '--',
        power: cast.daypower || cast.nightpower || '',
      }
    }
    // 回退：day内置天气或未知
    const dayWeather = (d as any).weather || '--'
    return {
      day: d.day,
      date: d.date || '',
      dayWeather,
      nightWeather: '',
      dayTemp: '--',
      nightTemp: '--',
      wind: '--',
      power: '',
    }
  })
}

export const WeatherDetailPlugin: TripCraftPlugin = {
  meta: {
    id: 'weather-detail',
    name: '天气预报',
    version: '1.0.0',
    description: '展示行程期间每日天气详情',
    icon: '🌤️',
    slot: 'sidebar',
  },

  render: (ctx: PluginContext) => {
    if (!ctx.plan) return null
    const forecasts = extractWeather(ctx)

    return (
      <div key="weather-detail" style={{
        padding: 12, borderRadius: 10, marginBottom: 8,
        background: 'rgba(15,23,42,0.5)', border: '1px solid rgba(34,211,240,0.1)',
        fontSize: 11,
      }}>
        <div style={{ color: '#94a3b8', fontWeight: 600, marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>🌤️ 天气预报</span>
          <span style={{ fontSize: 10, color: '#64748b' }}>{ctx.plan.destination}</span>
        </div>

        {forecasts.length === 0 ? (
          <div style={{ color: '#64748b', textAlign: 'center', padding: 8 }}>暂无天气数据</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {forecasts.map((f) => {
              const dayW = parseWeather(f.dayWeather)
              return (
                <div key={f.day} style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '6px 8px', borderRadius: 8,
                  background: 'rgba(0,0,0,0.15)',
                }}>
                  {/* 日期 */}
                  <span style={{ color: '#64748b', flexShrink: 0, minWidth: 36, textAlign: 'center', fontWeight: 600, fontSize: 10 }}>
                    {f.date ? f.date.slice(5).replace('-', '/') : `D${f.day}`}
                  </span>

                  {/* 天气emoji */}
                  <span style={{ fontSize: 16, flexShrink: 0 }}>{dayW.emoji}</span>

                  {/* 天气+温度 */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ color: '#e2e8f0', whiteSpace: 'nowrap' }}>
                      {f.dayWeather}
                      {f.nightWeather && f.nightWeather !== f.dayWeather && (
                        <span style={{ color: '#64748b' }}> → {f.nightWeather}</span>
                      )}
                    </div>
                    <div style={{ color: '#64748b', fontSize: 10 }}>
                      {f.dayTemp !== '--' ? `${f.dayTemp}°` : ''}
                      {f.nightTemp !== '--' && f.nightTemp !== f.dayTemp ? ` / ${f.nightTemp}°` : ''}
                      {f.wind !== '--' ? ` ${f.wind}${f.power}级` : ''}
                    </div>
                  </div>

                  {/* 温度条 */}
                  {f.dayTemp !== '--' && f.nightTemp !== '--' && (
                    <div style={{
                      width: 40, height: 4, borderRadius: 2, flexShrink: 0,
                      background: 'linear-gradient(90deg, #22d3f0, #fbbf24, #fb7185)',
                      opacity: 0.5,
                    }} />
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    )
  },
}
