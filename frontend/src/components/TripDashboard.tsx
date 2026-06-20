import {
  CalendarOutlined,
  CommentOutlined,
  EnvironmentOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import { lazy, Suspense, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { TravelPlan } from '../types/travel';

const ItineraryView = lazy(() => import('./ItineraryView'));
const MapPanel = lazy(() => import('./MapPanel'));
const RevisionHistory = lazy(() => import('./RevisionHistory'));
const AdjustmentChat = lazy(() => import('./AdjustmentChat'));

const LazyFallback = () => (
  <div className="lazy-loading">
    <div className="spinner" style={{ color: 'var(--neon-cyan)' }} />
    <span style={{ color: 'var(--text-muted)', marginTop: 12 }}>加载中...</span>
  </div>
);

interface Props {
  plan: TravelPlan;
  onPlanChange: (plan: TravelPlan) => void;
  onNewPlan: () => void;
  onEditPlan: () => void;
  onExport: (format: 'json' | 'markdown' | 'text' | 'preview') => void;
  onAdjust?: (instruction: string) => void;
}

const tabs = [
  { key: 'itinerary', icon: <CalendarOutlined />, label: '行程方案', color: '#22d3f0' },
  { key: 'map', icon: <EnvironmentOutlined />, label: '地图路线', color: '#2dd4bf' },
  { key: 'history', icon: <HistoryOutlined />, label: '审查历史', color: '#a78bfa' },
  { key: 'chat', icon: <CommentOutlined />, label: '调整对话', color: '#fbbf24' },
];

export default function TripDashboard({ plan, onPlanChange, onNewPlan, onEditPlan, onExport, onAdjust }: Props) {
  const [activeTab, setActiveTab] = useState('itinerary');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Enhanced Tab Navigation */}
      <div className="tab-nav circuit-border">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.key;
          return (
            <motion.button
              key={tab.key}
              className={`tab-btn ${isActive ? 'active scan-line-active' : ''}`}
              onClick={() => setActiveTab(tab.key)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              style={isActive ? {
                textShadow: `0 0 10px ${tab.color}`,
              } : undefined}
            >
              <span style={{ color: isActive ? tab.color : undefined }}>{tab.icon}</span>
              {tab.label}
            </motion.button>
          );
        })}
      </div>

      {/* Tab Content with animated transitions */}
      <div className="tab-content holographic-card">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
          >
            <Suspense fallback={<LazyFallback />}>
              {activeTab === 'itinerary' && <ItineraryView plan={plan} />}
              {activeTab === 'map' && <MapPanel plan={plan} />}
              {activeTab === 'history' && <RevisionHistory plan={plan} />}
              {activeTab === 'chat' && (
                <AdjustmentChat
                  key={plan?.plan_id}
                  plan={plan}
                  onPlanChange={onPlanChange}
                  onAdjust={onAdjust || (() => {})}
                />
              )}
            </Suspense>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
