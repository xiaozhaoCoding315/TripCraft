import { MessageOutlined } from '@ant-design/icons';
import { AnimatePresence, motion } from 'framer-motion';
import type { ReactNode } from 'react';

interface Props {
  open: boolean;
  onToggle: () => void;
  children: ReactNode;
}

export default function AssistantPanel({ open, onToggle, children }: Props) {
  return (
    <>
      {/* Toggle Button */}
      <motion.button
        className="assistant-toggle"
        onClick={onToggle}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.95 }}
        style={{
          position: 'fixed',
          right: open ? '380px' : '16px',
          bottom: '24px',
          width: '48px',
          height: '48px',
          borderRadius: '50%',
          background: open
            ? 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))'
            : 'var(--surface-glass)',
          border: '1px solid var(--surface-border)',
          color: open ? 'white' : 'var(--accent-primary)',
          cursor: 'pointer',
          zIndex: 50,
          backdropFilter: 'blur(12px)',
          boxShadow: open ? 'var(--glow-medium)' : 'var(--shadow-md)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '20px',
          transition: 'right 0.3s ease',
        }}
        title={open ? '关闭对话面板' : '打开对话面板'}
      >
        <MessageOutlined />
      </motion.button>

      {/* Panel */}
      <AnimatePresence>
        {open && (
          <motion.aside
            initial={{ width: 0, opacity: 0, x: 50 }}
            animate={{ width: '360px', opacity: 1, x: 0 }}
            exit={{ width: 0, opacity: 0, x: 50 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            style={{
              flexShrink: 0,
              overflow: 'hidden',
              position: 'sticky',
              top: '80px',
              alignSelf: 'flex-start',
              maxHeight: 'calc(100vh - 120px)',
            }}
          >
            <div
              className="card data-stream-vertical"
              style={{
                width: '360px',
                height: '100%',
                maxHeight: 'calc(100vh - 120px)',
                overflow: 'auto',
              }}
            >
              <div className="card-header" style={{ marginBottom: '12px' }}>
                💬 AI 对话调整
              </div>
              {children}
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  );
}
