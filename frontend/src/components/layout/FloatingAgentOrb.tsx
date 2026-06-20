import React, { useState, useRef, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ThunderboltOutlined, CloseOutlined } from '@ant-design/icons';
import type { AgentProgressEvent } from '../../types/travel';

interface FloatingAgentOrbProps {
  events: AgentProgressEvent[];
  planning: boolean;
  onNavigate?: () => void;
}

/**
 * FloatingAgentOrb - Draggable floating orb showing agent status
 * Pulses during planning, click to expand agent status summary
 */
const FloatingAgentOrb: React.FC<FloatingAgentOrbProps> = ({
  events,
  planning,
  onNavigate,
}) => {
  const [expanded, setExpanded] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });
  const posStart = useRef({ x: 0, y: 0 });
  const orbRef = useRef<HTMLDivElement>(null);

  // Default position: bottom-right
  useEffect(() => {
    if (position.x === 0 && position.y === 0) {
      setPosition({ x: window.innerWidth - 100, y: window.innerHeight - 180 });
    }
  }, [position]);

  // Get the latest events for each agent
  const agentStates = events.reduce((acc, event) => {
    acc[event.agent] = event;
    return acc;
  }, {} as Record<string, AgentProgressEvent>);

  const agentNames = ['weather', 'transport', 'accommodation', 'attraction', 'itinerary', 'critic'];

  const runningCount = agentNames.filter(
    (name) => agentStates[name]?.status === 'running'
  ).length;
  const completedCount = agentNames.filter(
    (name) => agentStates[name]?.status === 'success'
  ).length;

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      dragStart.current = { x: e.clientX, y: e.clientY };
      posStart.current = { ...position };
      setDragging(true);

      const handleMouseMove = (e: MouseEvent) => {
        const dx = e.clientX - dragStart.current.x;
        const dy = e.clientY - dragStart.current.y;
        setPosition({
          x: posStart.current.x + dx,
          y: posStart.current.y + dy,
        });
      };

      const handleMouseUp = () => {
        setDragging(false);
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };

      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    },
    [position]
  );

  const handleClick = useCallback(() => {
    if (!dragging) {
      setExpanded(!expanded);
    }
  }, [dragging, expanded]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'var(--neon-amber)';
      case 'success': return 'var(--neon-green)';
      case 'error': return 'var(--neon-rose)';
      default: return 'var(--text-muted)';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running': return '◉';
      case 'success': return '●';
      case 'error': return '⚠';
      case 'queued': return '○';
      default: return '·';
    }
  };

  if (!planning && events.length === 0) return null;

  return (
    <>
      {/* The floating orb */}
      <motion.div
        ref={orbRef}
        className={`agent-orb ${planning ? 'pulse' : ''}`}
        style={{
          position: 'fixed',
          left: position.x,
          top: position.y,
          zIndex: 50,
        }}
        onMouseDown={handleMouseDown}
        onClick={handleClick}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.95 }}
      >
        <div className="agent-orb-ring" />
        <span className="agent-orb-inner">
          {planning ? '⚡' : '✨'}
        </span>
        {/* Progress indicator */}
        {planning && (
          <div
            style={{
              position: 'absolute',
              bottom: -4,
              left: '50%',
              transform: 'translateX(-50%)',
              fontSize: 10,
              fontWeight: 600,
              color: 'var(--neon-cyan)',
              textShadow: '0 0 8px rgba(34,211,240,0.5)',
            }}
          >
            {completedCount}/{agentNames.length}
          </div>
        )}
      </motion.div>

      {/* Expanded agent status panel */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 10 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
            style={{
              position: 'fixed',
              right: 24,
              bottom: 200,
              width: 260,
              padding: 16,
              background: 'rgba(10, 15, 29, 0.9)',
              backdropFilter: 'blur(24px)',
              border: '1px solid var(--surface-border)',
              borderRadius: 16,
              boxShadow: '0 8px 32px rgba(0,0,0,0.5), 0 0 30px rgba(34,211,240,0.15)',
              zIndex: 50,
            }}
          >
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 12,
            }}>
              <span style={{
                fontSize: 13,
                fontWeight: 600,
                color: 'var(--neon-cyan)',
              }}>
                ⚡ Agent Status
              </span>
              <CloseOutlined
                style={{ color: 'var(--text-muted)', cursor: 'pointer', fontSize: 12 }}
                onClick={() => setExpanded(false)}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {agentNames.map((name) => {
                const state = agentStates[name];
                const status = state?.status || 'queued';
                return (
                  <div
                    key={name}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '6px 10px',
                      borderRadius: 8,
                      background: 'rgba(26, 37, 56, 0.4)',
                      border: `1px solid ${status === 'running' ? 'rgba(251,191,36,0.3)' : 'transparent'}`,
                    }}
                  >
                    <span style={{
                      color: getStatusColor(status),
                      fontSize: 10,
                      width: 14,
                      textAlign: 'center',
                    }}>
                      {getStatusIcon(status)}
                    </span>
                    <span style={{
                      flex: 1,
                      fontSize: 12,
                      color: status === 'running' ? 'var(--neon-amber)' : 'var(--text-secondary)',
                      textTransform: 'capitalize',
                    }}>
                      {name}
                    </span>
                    {status === 'running' && (
                      <div className="spinner" style={{ width: 12, height: 12, color: 'var(--neon-amber)' }} />
                    )}
                    {status === 'success' && (
                      <span style={{ color: 'var(--neon-green)', fontSize: 10 }}>✓</span>
                    )}
                  </div>
                );
              })}
            </div>

            {planning && (
              <div style={{ marginTop: 12 }}>
                <div style={{
                  height: 3,
                  background: 'var(--bg-surface)',
                  borderRadius: 2,
                  overflow: 'hidden',
                }}>
                  <div
                    className="progress-shimmer"
                    style={{
                      height: '100%',
                      width: `${(completedCount / agentNames.length) * 100}%`,
                      background: 'linear-gradient(90deg, var(--neon-cyan), var(--neon-teal))',
                      borderRadius: 2,
                      transition: 'width 0.5s ease',
                    }}
                  />
                </div>
                <div style={{
                  fontSize: 10,
                  color: 'var(--text-muted)',
                  textAlign: 'center',
                  marginTop: 4,
                }}>
                  {completedCount} / {agentNames.length} agents complete
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default FloatingAgentOrb;
