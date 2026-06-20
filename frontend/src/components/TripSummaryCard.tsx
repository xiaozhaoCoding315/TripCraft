import { WalletOutlined } from '@ant-design/icons';
import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';
import type { TravelPlan } from '../types/travel';

const typeColors: Record<string, string> = {
  transport: '#2dd4bf',
  attraction: '#4ade80',
  meal: '#fbbf24',
  hotel: '#a78bfa',
  rest: '#22d3f0',
  note: '#fb7185',
};

const typeLabels: Record<string, string> = {
  transport: '交通',
  attraction: '景点',
  meal: '餐饮',
  hotel: '住宿',
  rest: '休息',
  note: '备注',
};

interface Props {
  plan: TravelPlan;
}

export default function TripSummaryCard({ plan }: Props) {
  const costByType = plan.days.reduce(
    (acc, day) => {
      day.items.forEach((item) => {
        if (item.cost && item.cost > 0) {
          acc[item.type] = (acc[item.type] || 0) + item.cost;
        }
      });
      return acc;
    },
    {} as Record<string, number>
  );

  const totalCost = plan.total_estimated_cost || Object.values(costByType).reduce((a, b) => a + b, 0);
  const costEntries = Object.entries(costByType).sort((a, b) => b[1] - a[1]);

  return (
    <div className="card holographic-card" style={{ marginBottom: 12, padding: 16 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
        <div
          style={{
            width: 42,
            height: 42,
            borderRadius: 12,
            background: 'linear-gradient(135deg, #22d3f0, #2dd4bf)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 16px rgba(34,211,240,0.3)',
          }}
        >
          <WalletOutlined style={{ color: '#060b14', fontSize: 18 }} />
        </div>
        <div>
          <div style={{ fontSize: 15, fontWeight: 600, color: '#e2e8f0' }}>
            {plan.destination} 行程概览
          </div>
          <div style={{ fontSize: 11, color: '#64748b' }}>
            {(plan as any).departure_city ? `从 ${(plan as any).departure_city} 出发` : '旅行计划'}
          </div>
        </div>
      </div>

      {/* Stats row */}
      <div style={{ display: 'flex', gap: 20, marginBottom: 14, flexWrap: 'wrap' }}>
        <div style={{ textAlign: 'center' }}>
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 200 }}
            style={{ fontSize: 20, fontWeight: 700, color: '#22d3f0' }}
          >
            {plan.days.length}
          </motion.div>
          <div style={{ fontSize: 10, color: '#64748b' }}>天</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 200, delay: 0.1 }}
            style={{ fontSize: 20, fontWeight: 700, color: '#4ade80' }}
          >
            ¥{(totalCost || 0).toLocaleString()}
          </motion.div>
          <div style={{ fontSize: 10, color: '#64748b' }}>预计费用</div>
        </div>
        {/* 每日天气速览 */}
        {plan.days.some(d => (d as any).weather) && (
          <div style={{ flex: 1, minWidth: 120 }}>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {plan.days.slice(0, 7).map(d => (
                <span key={d.day} style={{
                  fontSize: 10, padding: '2px 6px', borderRadius: 8,
                  background: 'rgba(34,211,240,0.08)', border: '1px solid rgba(34,211,240,0.15)',
                  color: '#94a3b8', whiteSpace: 'nowrap',
                }} title={(d as any).weather || ''}>
                  D{d.day} {(d as any).weather ? ((d as any).weather).slice(0, 8) : '--'}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Cost breakdown bar */}
      {totalCost > 0 && (
        <div style={{ marginTop: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontSize: 11, color: '#94a3b8' }}>费用构成</span>
            <span style={{ fontSize: 11, color: '#64748b' }}>¥{totalCost.toLocaleString()}</span>
          </div>
          {/* Animated bar chart */}
          <div style={{ display: 'flex', height: 8, borderRadius: 4, overflow: 'hidden', gap: 1 }}>
            {costEntries.map(([type, cost]) => (
              <motion.div
                key={type}
                initial={{ width: 0 }}
                animate={{ width: `${(cost / totalCost) * 100}%` }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
                style={{
                  background: typeColors[type] || '#22d3f0',
                  boxShadow: `0 0 8px ${typeColors[type]}40`,
                }}
                title={`${typeLabels[type] || type}: ¥${cost}`}
              />
            ))}
          </div>
          {/* Legend */}
          <div style={{ display: 'flex', gap: 12, marginTop: 8, flexWrap: 'wrap' }}>
            {costEntries.map(([type, cost]) => (
              <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <div
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: typeColors[type] || '#22d3f0',
                    boxShadow: `0 0 6px ${typeColors[type]}60`,
                  }}
                />
                <span style={{ fontSize: 10, color: '#94a3b8' }}>
                  {typeLabels[type] || type} ¥{cost}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
