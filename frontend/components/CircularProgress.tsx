'use client';

import React, { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface CircularProgressProps {
  value: number;
  size?: number;
  strokeWidth?: number;
  color?: string;
  label?: string;
  sublabel?: string;
}

export default function CircularProgress({
  value,
  size = 140,
  strokeWidth = 8,
  color = '#141413',
  label = 'Confidence',
  sublabel = 'ML Score',
}: CircularProgressProps) {
  const progress = Math.max(0, Math.min(100, value));

  const { radius, circumference, strokeDashoffset, tipX, tipY } = useMemo(() => {
    const r = (size - strokeWidth) / 2;
    const c = 2 * Math.PI * r;
    const offset = c * (1 - progress / 100);
    const angle = (progress / 100) * 2 * Math.PI - Math.PI / 2;
    const cx = size / 2;
    const cy = size / 2;
    const x = cx + r * Math.cos(angle);
    const y = cy + r * Math.sin(angle);
    return { radius: r, circumference: c, strokeDashoffset: offset, tipX: x, tipY: y };
  }, [progress, size, strokeWidth]);

  return (
    <motion.div
      style={{ position: 'relative', width: size, height: size }}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ type: 'spring', stiffness: 200, damping: 20, duration: 0.6 }}
    >
      {/* Background track */}
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255, 255, 255, 0.1)"
          strokeWidth={strokeWidth}
        />

        {/* Progress ring */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset }}
          transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
        />

        {/* Tip dot */}
        <AnimatePresence>
          {progress > 2 && (
            <motion.circle
              key="tip"
              cx={tipX}
              cy={tipY}
              r={strokeWidth / 2 + 1}
              fill={color}
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0 }}
              transition={{ type: 'spring', stiffness: 400, damping: 20 }}
            />
          )}
        </AnimatePresence>
      </svg>

      {/* Center content */}
      <motion.div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 2,
          zIndex: 1,
        }}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.3 }}
      >
        <motion.span
          style={{
            fontSize: size < 100 ? 18 : 26,
            fontWeight: 800,
            color,
            fontFamily: "'JetBrains Mono', monospace",
            lineHeight: 1,
          }}
        >
          <AnimatePresence mode="wait">
            <motion.span
              key={Math.round(progress)}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              {Math.round(progress)}%
            </motion.span>
          </AnimatePresence>
        </motion.span>
        {label && (
          <motion.span
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.3 }}
            style={{
              fontSize: 10,
              fontWeight: 600,
              color: '#A1A1AA',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              textAlign: 'center',
              maxWidth: size * 0.6,
            }}
          >
            {label}
          </motion.span>
        )}
        {sublabel && (
          <motion.span
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6, duration: 0.3 }}
            style={{
              fontSize: 9,
              color: '#71717A',
              textAlign: 'center',
            }}
          >
            {sublabel}
          </motion.span>
        )}
      </motion.div>
    </motion.div>
  );
}