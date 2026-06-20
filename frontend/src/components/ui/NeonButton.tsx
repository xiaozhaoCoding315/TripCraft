import React from 'react';

interface NeonButtonProps {
  children: React.ReactNode;
  variant?: 'primary' | 'neon' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  className?: string;
  style?: React.CSSProperties;
  icon?: React.ReactNode;
  type?: 'button' | 'submit';
  ripple?: boolean;
}

/**
 * NeonButton - Tech-styled button with glow and ripple effects
 */
const NeonButton: React.FC<NeonButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  onClick,
  className = '',
  style,
  icon,
  type = 'button',
  ripple = true,
}) => {
  const sizeStyles: Record<string, React.CSSProperties> = {
    sm: { padding: '6px 14px', fontSize: 'var(--text-sm)' },
    md: { padding: '10px 20px', fontSize: 'var(--text-base)' },
    lg: { padding: '14px 28px', fontSize: 'var(--text-lg)' },
  };

  const variantClass = {
    primary: 'btn-primary',
    neon: 'btn-neon',
    ghost: 'btn-ghost',
  }[variant];

  const rippleClass = ripple ? 'btn-ripple' : '';

  return (
    <button
      type={type}
      className={`btn-base ${variantClass} ${rippleClass} ${className}`}
      disabled={disabled || loading}
      onClick={onClick}
      style={{
        ...sizeStyles[size],
        ...style,
      }}
    >
      {loading ? (
        <span className="spinner" style={{ width: 16, height: 16 }} />
      ) : icon ? (
        <span style={{ display: 'flex', alignItems: 'center' }}>{icon}</span>
      ) : null}
      {children}
    </button>
  );
};

export default NeonButton;
