import React, { useEffect, useState, useRef } from 'react';

interface AnimatedNumberProps {
  value: number;
  duration?: number;      // animation duration in ms, default 800
  prefix?: string;        // e.g., "¥"
  suffix?: string;        // e.g., "元"
  className?: string;
  style?: React.CSSProperties;
  decimals?: number;      // decimal places, default 0
  easing?: (t: number) => number;
}

/**
 * AnimatedNumber - Smoothly counts up/down to a target value
 * Used for costs, distances, counts
 */
const AnimatedNumber: React.FC<AnimatedNumberProps> = ({
  value,
  duration = 800,
  prefix = '',
  suffix = '',
  className = '',
  style,
  decimals = 0,
  easing,
}) => {
  const [displayValue, setDisplayValue] = useState(value);
  const prevValue = useRef(value);
  const frameRef = useRef<number>(0);

  useEffect(() => {
    const startValue = prevValue.current;
    const endValue = value;
    const diff = endValue - startValue;

    // No animation needed
    if (diff === 0) {
      setDisplayValue(endValue);
      return;
    }

    const startTime = performance.now();

    // Default easing: ease-out cubic
    const defaultEasing = (t: number) => 1 - Math.pow(1 - t, 3);
    const easeFn = easing || defaultEasing;

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easedProgress = easeFn(progress);

      const current = startValue + diff * easedProgress;
      setDisplayValue(current);

      if (progress < 1) {
        frameRef.current = requestAnimationFrame(animate);
      }
    };

    frameRef.current = requestAnimationFrame(animate);
    prevValue.current = endValue;

    return () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }
    };
  }, [value, duration, easing]);

  const formatted = decimals > 0
    ? displayValue.toFixed(decimals)
    : Math.round(displayValue).toLocaleString();

  return (
    <span className={`count-up ${className}`} style={style}>
      {prefix}{formatted}{suffix}
    </span>
  );
};

export default AnimatedNumber;
