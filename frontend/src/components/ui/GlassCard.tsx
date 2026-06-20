import React from 'react';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  variant?: 'default' | 'deep' | 'neon';
  hover?: boolean;
  onClick?: () => void;
  style?: React.CSSProperties;
}

/**
 * GlassCard - Frosted glass card with depth effect
 * Variants: default (standard glass), deep (darker, more blur), neon (glowing gradient border)
 */
const GlassCard: React.FC<GlassCardProps> = ({
  children,
  className = '',
  variant = 'default',
  hover = true,
  onClick,
  style,
}) => {
  const baseClasses = {
    default: 'glass-card',
    deep: 'glass-card-deep',
    neon: 'neon-card',
  };

  const hoverClass = hover ? 'card-hover' : '';

  return (
    <div
      className={`${baseClasses[variant]} ${hoverClass} ${className}`}
      onClick={onClick}
      style={{
        cursor: onClick ? 'pointer' : undefined,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

export default GlassCard;
