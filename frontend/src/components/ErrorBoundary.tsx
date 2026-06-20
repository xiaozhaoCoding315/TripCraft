import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Button, Result } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <Result
          status="error"
          title="页面出现错误"
          subTitle={this.state.error?.message || '未知错误'}
          extra={
            <Button type="primary" icon={<ReloadOutlined />} onClick={this.handleReset}>
              重试
            </Button>
          }
          style={{
            background: 'var(--surface-glass)',
            borderRadius: 'var(--radius-lg)',
            padding: 'var(--space-8)',
            border: '1px solid var(--surface-border)',
          }}
        />
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
