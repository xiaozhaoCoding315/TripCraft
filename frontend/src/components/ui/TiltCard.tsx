import React, { useRef, useState, useCallback } from 'react';

interface TiltCardProps {
  children: React.ReactNode;
  className?: string;
  maxTilt?: number;       // max rotation in degrees, default 5
  perspective?: number;   // CSS perspective, default 1000
  scale?: number;         // hover scale, default 1.02
  style?: React.CSSProperties;
}

/**
 * TiltCard - 3D perspective card that tilts toward the mouse cursor
 * Creates a depth-parallax effect for cards
 */
const TiltCard: React.FC<TiltCardProps> = ({
  children,
  className = '',
  maxTilt = 5,
  perspective = 1000,
  scale = 1.02,
  style,
}) => {
  const cardRef = useRef<HTMLDivElement>(null);
  const [transform, setTransform] = useState('');
  const [glow, setGlow] = useState('');

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!cardRef.current) return;

      const rect = cardRef.current.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;

      // Calculate mouse position relative to center (-1 to 1)
      const mouseX = (e.clientX - centerX) / (rect.width / 2);
      const mouseY = (e.clientY - centerY) / (rect.height / 2);

      // Calculate tilt
      const rotateX = mouseY * -maxTilt;
      const rotateY = mouseX * maxTilt;

      setTransform(
        `perspective(${perspective}px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(${scale})`
      );

      // Dynamic glow follows mouse
      const glowX = (e.clientX / rect.width) * 100;
      const glowY = (e.clientY / rect.height) * 100;
      setGlow(
        `radial-gradient(circle at ${glowX}% ${glowY}%, rgba(34,211,240,0.12) 0%, transparent 60%)`
      );
    },
    [maxTilt, perspective, scale]
  );

  const handleMouseLeave = useCallback(() => {
    setTransform(`perspective(${perspective}px) rotateX(0deg) rotateY(0deg) scale(1)`);
    setGlow('');
  }, [perspective]);

  return (
    <div
      ref={cardRef}
      className={`tilt-card ${className}`}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        transform,
        transition: 'transform 0.1s ease-out, box-shadow 0.3s ease',
        position: 'relative',
        overflow: 'hidden',
        ...style,
      }}
    >
      {/* Dynamic glow overlay */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: glow,
          pointerEvents: 'none',
          transition: 'opacity 0.2s',
          zIndex: 0,
        }}
      />
      {/* Content */}
      <div style={{ position: 'relative', zIndex: 1 }}>{children}</div>
    </div>
  );
};

export default TiltCard;
