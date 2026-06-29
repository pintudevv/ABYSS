'use client';

import React, { useEffect, useRef, useState } from 'react';

interface CircularProgressProps {
  /** 0–100 */
  value: number;
  /** px */
  size?: number;
  strokeWidth?: number;
  color?: string;
  trackColor?: string;
  label?: string;
  sublabel?: string;
  animate?: boolean;
}

export default function CircularProgress({
  value,
  size = 140,
  strokeWidth = 8,
  color = '#6366f1',
  trackColor = 'rgba(255,255,255,0.06)',
  label,
  sublabel,
  animate = true,
}: CircularProgressProps) {
  const [displayed, setDisplayed] = useState(animate ? 0 : value);
  const rafRef = useRef<number | null>(null);
  const startRef = useRef<number | null>(null);
  const DURATION = 1200; // ms

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(100, Math.max(0, displayed));
  const dashOffset = circumference - (progress / 100) * circumference;

  useEffect(() => {
    if (!animate) {
      setDisplayed(value);
      return;
    }

    const from = displayed;
    const to = value;

    const tick = (timestamp: number) => {
      if (startRef.current === null) startRef.current = timestamp;
      const elapsed = timestamp - startRef.current;
      const t = Math.min(elapsed / DURATION, 1);
      // Apple spring easing approximation
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplayed(from + (to - from) * eased);

      if (t < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        setDisplayed(to);
      }
    };

    startRef.current = null;
    rafRef.current = requestAnimationFrame(tick);

    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, animate]);

  const cx = size / 2;
  const cy = size / 2;

  return (
    <div
      style={{
        position: 'relative',
        width: size,
        height: size,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
      }}
    >
      {/* Outer glow ring */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '50%',
          background: `radial-gradient(circle, ${color}18 0%, transparent 70%)`,
          pointerEvents: 'none',
        }}
      />

      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ position: 'absolute', top: 0, left: 0, transform: 'rotate(-90deg)' }}
      >
        {/* Track */}
        <circle
          cx={cx}
          cy={cy}
          r={radius}
          fill="none"
          stroke={trackColor}
          strokeWidth={strokeWidth}
        />

        {/* Outer decorative ring */}
        <circle
          cx={cx}
          cy={cy}
          r={radius + strokeWidth / 2 + 4}
          fill="none"
          stroke="rgba(255,255,255,0.04)"
          strokeWidth={1}
          strokeDasharray="4 6"
        />

        {/* Progress arc */}
        <circle
          cx={cx}
          cy={cy}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          style={{
            filter: `drop-shadow(0 0 8px ${color}90)`,
            transition: animate ? 'none' : 'stroke-dashoffset 0.8s cubic-bezier(0.16,1,0.3,1)',
          }}
        />

        {/* Tip dot */}
        {progress > 2 && (
          <circle
            cx={cx + radius * Math.cos((2 * Math.PI * progress) / 100 - Math.PI / 2)}
            cy={cy + radius * Math.sin((2 * Math.PI * progress) / 100 - Math.PI / 2)}
            r={strokeWidth / 2 + 1}
            fill={color}
            style={{ filter: `drop-shadow(0 0 6px ${color})` }}
            transform={`rotate(0 ${cx} ${cy})`}
          />
        )}
      </svg>

      {/* Center content */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 2,
          zIndex: 1,
        }}
      >
        <span
          style={{
            fontSize: size < 100 ? 18 : 26,
            fontWeight: 700,
            color: color,
            fontFamily: "'Inter', sans-serif",
            lineHeight: 1,
            textShadow: `0 0 16px ${color}80`,
          }}
        >
          {Math.round(progress)}%
        </span>
        {label && (
          <span
            style={{
              fontSize: 10,
              fontWeight: 600,
              color: 'rgba(255,255,255,0.5)',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              textAlign: 'center',
              maxWidth: size * 0.6,
            }}
          >
            {label}
          </span>
        )}
        {sublabel && (
          <span
            style={{
              fontSize: 9,
              color: 'rgba(255,255,255,0.3)',
              textAlign: 'center',
            }}
          >
            {sublabel}
          </span>
        )}
      </div>
    </div>
  );
}
