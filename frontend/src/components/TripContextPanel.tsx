import { DeleteOutlined, DownloadOutlined, HistoryOutlined, PlusOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { motion } from 'framer-motion';
import type { MemoryItem, PlanSummary } from '../types/travel';
import TripSummaryCard from './TripSummaryCard';
import type { TravelPlan } from '../types/travel';

interface Props {
  plan: TravelPlan;
  plans: PlanSummary[];
  memory: MemoryItem[];
  currentPlanId: string | null;
  onLoadPlan: (planId: string) => Promise<void>;
  onDeletePlan: (planId: string) => void;
  onNewPlan: () => void;
  onEditPlan: () => void;
  onExport: (format: 'json' | 'markdown' | 'text' | 'preview') => void;
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
  general: { label: '通用', color: '#64748b' },
};

export default function TripContextPanel({
  plan,
  plans,
  memory,
  currentPlanId,
  onLoadPlan,
  onDeletePlan,
  onNewPlan,
  onEditPlan,
  onExport,
}: Props) {
  return (
    <>
      {/* Trip Summary Card */}
      <TripSummaryCard plan={plan} />

      {/* Quick Actions */}
      <div className="card circuit-border" style={{ padding: 14 }}>
        <div className="card-header">
          <ThunderboltOutlined /> 快捷操作
        </div>
        <div className="quick-actions">
          <button className="btn-secondary" onClick={onEditPlan}>
            💬 调整行程
          </button>
          <button className="btn-secondary" onClick={onNewPlan}>
            <PlusOutlined /> 新建行程
          </button>
          <button className="btn-secondary" onClick={() => onExport('markdown')}>
            <DownloadOutlined /> 导出 Markdown
          </button>
          <button className="btn-secondary" onClick={() => onExport('preview' as any)}>
            🤖 AI 预览格式化导出
          </button>
        </div>
      </div>

      {/* Historical Plans */}
      <div className="card">
        <div className="card-header">
          <HistoryOutlined /> 历史行程 ({plans.length})
        </div>
        {plans.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: '8px 0' }}>
            暂无历史行程
          </div>
        ) : (
          <div className="plan-list">
            {plans.slice(0, 5).map((p) => (
              <motion.div
                key={p.plan_id}
                className={`plan-item ${currentPlanId === p.plan_id ? 'active' : ''}`}
                onClick={() => onLoadPlan(p.plan_id)}
                whileHover={{ x: 4 }}
              >
                <div className="plan-item-info">
                  <span className="plan-item-city">{p.destination}</span>
                  <span className="plan-item-meta">
                    {p.days}天 · ¥{Math.round(p.total_estimated_cost || 0).toLocaleString()}
                  </span>
                </div>
                <div className="plan-item-actions">
                  <button
                    className="btn-icon delete"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeletePlan(p.plan_id);
                    }}
                    title="删除行程"
                  >
                    <DeleteOutlined style={{ fontSize: 12 }} />
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Memory Panel */}
      {memory.length > 0 && (
        <div className="card">
          <details>
            <summary className="card-header">
              <HistoryOutlined /> 用户偏好 ({memory.length})
            </summary>
            <div className="memory-list">
              {memory.map((item) => {
                const cat = categoryLabels[item.category] || { label: item.category, color: '#64748b' };
                return (
                  <div key={item.key} className="memory-item">
                    <span
                      className="memory-tag"
                      style={{ background: cat.color }}
                    >
                      {cat.label}
                    </span>
                    <span className="memory-value">{item.value}</span>
                  </div>
                );
              })}
            </div>
          </details>
        </div>
      )}
    </>
  );
}
