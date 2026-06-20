import { Alert, Card, Empty, List, Tag } from 'antd';
import { AuditOutlined, CheckCircleOutlined, WarningOutlined } from '@ant-design/icons';
import type { TravelPlan } from '../types/travel';

const dimensionLabels: Record<string, string> = {
  physical: '体力评估',
  time: '时间评估',
  budget: '预算评估',
  weather: '天气评估',
  data: '数据检查',
  overall: '综合评估',
};

export default function RevisionHistory({ plan }: { plan?: TravelPlan }) {
  return (
    <Card
      title={
        <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AuditOutlined style={{ color: 'var(--accent-primary)' }} />
          Critic 审查与修改历史
        </span>
      }
      className="glass-card"
      style={{ borderColor: 'var(--surface-border)' }}
    >
      {/* Explanation header */}
      <div
        style={{
          padding: '10px 14px',
          marginBottom: '16px',
          background: 'rgba(99, 179, 237, 0.08)',
          border: '1px solid rgba(99, 179, 237, 0.15)',
          borderRadius: '8px',
          fontSize: '13px',
          color: 'var(--text-secondary)',
          lineHeight: 1.6,
        }}
      >
        💡 <strong style={{ color: 'var(--accent-primary)' }}>Critic 智能审查</strong>从体力、时间、预算、天气四个维度评估行程合理性。
        发现问题会自动返回重新编排（最多 3 轮），确保最终行程质量。
      </div>

      {!plan?.revisions.length ? (
        <Empty
          description="规划完成后展示 v1 → v2 → v3 的审查意见"
          style={{ color: 'var(--text-muted)' }}
        />
      ) : (
        <List
          dataSource={plan.revisions}
          renderItem={(revision, index) => (
            <List.Item
              style={{
                background: 'rgba(18, 24, 41, 0.5)',
                borderRadius: '12px',
                marginBottom: '12px',
                border: '1px solid var(--surface-border)',
                transition: 'all 0.3s ease',
                animation: `slideInRight 0.3s ease ${index * 0.15}s both`,
              }}
            >
              <List.Item.Meta
                title={
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Tag
                      color={revision.passed ? 'green' : 'orange'}
                      style={{
                        background: revision.passed
                          ? 'rgba(104, 211, 145, 0.15)'
                          : 'rgba(246, 173, 85, 0.15)',
                        borderColor: revision.passed
                          ? 'rgba(104, 211, 145, 0.3)'
                          : 'rgba(246, 173, 85, 0.3)',
                        color: revision.passed
                          ? 'var(--status-success)'
                          : 'var(--status-running)',
                      }}
                    >
                      v{revision.version}
                    </Tag>
                    <span style={{ color: 'var(--text-primary)' }}>{revision.summary}</span>
                    {revision.passed && (
                      <CheckCircleOutlined style={{ color: 'var(--status-success)' }} />
                    )}
                  </div>
                }
                description={
                  <div style={{ marginTop: '8px' }}>
                    {revision.comments.length === 0 ? (
                      <span style={{ color: 'var(--status-success)', fontSize: '13px' }}>
                        ✓ 所有检查项通过
                      </span>
                    ) : (
                      revision.comments.map((comment, idx) => (
                        <Alert
                          key={idx}
                          type={
                            comment.severity === 'critical'
                              ? 'error'
                              : comment.severity === 'warning'
                              ? 'warning'
                              : 'info'
                          }
                          message={
                            <span style={{ fontWeight: 500 }}>
                              {dimensionLabels[comment.dimension] || comment.dimension}：{comment.message}
                            </span>
                          }
                          description={comment.suggestion}
                          showIcon
                          icon={
                            comment.severity === 'warning' ? (
                              <WarningOutlined style={{ color: 'var(--status-running)' }} />
                            ) : undefined
                          }
                          style={{
                            marginBottom: 8,
                            background:
                              comment.severity === 'critical'
                                ? 'rgba(252, 129, 129, 0.1)'
                                : comment.severity === 'warning'
                                ? 'rgba(246, 173, 85, 0.1)'
                                : 'rgba(99, 179, 237, 0.1)',
                            border:
                              comment.severity === 'critical'
                                ? '1px solid rgba(252, 129, 129, 0.3)'
                                : comment.severity === 'warning'
                                ? '1px solid rgba(246, 173, 85, 0.3)'
                                : '1px solid rgba(99, 179, 237, 0.3)',
                          }}
                        />
                      ))
                    )}
                  </div>
                }
              />
            </List.Item>
          )}
        />
      )}
    </Card>
  );
}
