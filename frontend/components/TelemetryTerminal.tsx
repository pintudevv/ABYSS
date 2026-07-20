'use client';

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, Shield, Pause, Play, Copy, Check, Filter, Maximize2, Minimize2, Radio } from 'lucide-react';
import type { TelemetryLog } from '@/lib/api';

interface TelemetryTerminalProps {
  logs: TelemetryLog[];
  isComplete?: boolean;
  isFailed?: boolean;
}

export default function TelemetryTerminal({ logs, isComplete, isFailed }: TelemetryTerminalProps) {
  const [filter, setFilter] = useState<'ALL' | 'HOOK' | 'BLOCK' | 'MOCK' | 'WARN' | 'ML'>('ALL');
  const [autoScroll, setAutoScroll] = useState(true);
  const [copied, setCopied] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const handleCopy = () => {
    const text = logs
      .map((l) => `[${l.timestamp}] [${l.stage}] [${l.level}] ${l.message}`)
      .join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const filteredLogs = logs.filter((log) => {
    if (filter !== 'ALL' && log.level !== filter && !log.stage.includes(filter)) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        log.message.toLowerCase().includes(q) ||
        log.stage.toLowerCase().includes(q) ||
        log.level.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const getLevelStyle = (level: TelemetryLog['level']) => {
    switch (level) {
      case 'HOOK':
        return { color: '#00D2FF', bg: 'rgba(0, 210, 255, 0.12)', border: 'rgba(0, 210, 255, 0.3)', icon: '⚡' };
      case 'BLOCK':
        return { color: '#FF2E55', bg: 'rgba(255, 46, 85, 0.12)', border: 'rgba(255, 46, 85, 0.3)', icon: '🛡️' };
      case 'MOCK':
        return { color: '#A855F7', bg: 'rgba(168, 85, 247, 0.12)', border: 'rgba(168, 85, 247, 0.3)', icon: '🍯' };
      case 'WARN':
        return { color: '#F59E0B', bg: 'rgba(245, 158, 11, 0.12)', border: 'rgba(245, 158, 11, 0.3)', icon: '⚠️' };
      case 'SUCCESS':
        return { color: '#00E599', bg: 'rgba(0, 229, 153, 0.12)', border: 'rgba(0, 229, 153, 0.3)', icon: '✓' };
      case 'ERROR':
        return { color: '#EF4444', bg: 'rgba(239, 68, 68, 0.15)', border: 'rgba(239, 68, 68, 0.4)', icon: '✖' };
      default:
        return { color: '#818CF8', bg: 'rgba(129, 140, 248, 0.1)', border: 'rgba(129, 140, 248, 0.2)', icon: 'ℹ' };
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      style={{
        marginTop: 24,
        background: '#07070A',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: 12,
        overflow: 'hidden',
        boxShadow: '0 20px 50px rgba(0,0,0,0.6), 0 0 1px rgba(255,255,255,0.1)',
      }}
    >
      {/* Terminal Header */}
      <div
        style={{
          background: '#0D0D14',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          padding: '10px 16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        {/* Title & OS Traffic Control Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ display: 'flex', gap: 6 }}>
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#FF5F56' }} />
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#FFBD2E' }} />
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#27C93F' }} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Terminal size={14} color="#00E599" />
            <span
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 12,
                fontWeight: 700,
                color: '#F4F4F6',
                letterSpacing: '0.04em',
              }}
            >
              ABYSS TELEMETRY STREAM
            </span>
          </div>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '2px 8px',
              borderRadius: 20,
              background: isComplete ? 'rgba(0,229,153,0.1)' : isFailed ? 'rgba(239,68,68,0.1)' : 'rgba(0,210,255,0.1)',
              border: `1px solid ${isComplete ? 'rgba(0,229,153,0.3)' : isFailed ? 'rgba(239,68,68,0.3)' : 'rgba(0,210,255,0.3)'}`,
            }}
          >
            {!isComplete && !isFailed && (
              <Radio size={10} color="#00D2FF" style={{ animation: 'pulse 1.5s infinite' }} />
            )}
            <span
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 10,
                fontWeight: 700,
                color: isComplete ? '#00E599' : isFailed ? '#EF4444' : '#00D2FF',
              }}
            >
              {isComplete ? 'REPORT READY' : isFailed ? 'FAILED' : 'LIVE STREAM'}
            </span>
          </div>
        </div>

        {/* Terminal Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Filters */}
          <div style={{ display: 'flex', background: 'rgba(255,255,255,0.03)', borderRadius: 6, padding: 2, border: '1px solid rgba(255,255,255,0.06)' }}>
            {(['ALL', 'HOOK', 'BLOCK', 'MOCK', 'WARN'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                style={{
                  padding: '3px 8px',
                  borderRadius: 4,
                  border: 'none',
                  background: filter === f ? 'rgba(255,255,255,0.12)' : 'transparent',
                  color: filter === f ? '#FFFFFF' : '#A1A1AA',
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 10,
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {f}
              </button>
            ))}
          </div>

          {/* Auto-scroll */}
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            title={autoScroll ? 'Pause auto-scroll' : 'Enable auto-scroll'}
            style={{
              padding: '4px 8px',
              borderRadius: 6,
              background: autoScroll ? 'rgba(0,229,153,0.1)' : 'rgba(255,255,255,0.05)',
              border: `1px solid ${autoScroll ? 'rgba(0,229,153,0.3)' : 'rgba(255,255,255,0.1)'}`,
              color: autoScroll ? '#00E599' : '#A1A1AA',
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            {autoScroll ? <Pause size={10} /> : <Play size={10} />}
            {autoScroll ? 'AUTOSCROLL' : 'PAUSED'}
          </button>

          {/* Copy */}
          <button
            onClick={handleCopy}
            title="Copy logs to clipboard"
            style={{
              padding: 5,
              borderRadius: 6,
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.1)',
              color: copied ? '#00E599' : '#A1A1AA',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            {copied ? <Check size={12} /> : <Copy size={12} />}
          </button>

          {/* Expand */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? 'Collapse' : 'Expand'}
            style={{
              padding: 5,
              borderRadius: 6,
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.1)',
              color: '#A1A1AA',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            {isExpanded ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
          </button>
        </div>
      </div>

      {/* Terminal Log Viewport */}
      <div
        style={{
          height: isExpanded ? 480 : 260,
          overflowY: 'auto',
          padding: 16,
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 12,
          lineHeight: 1.6,
          transition: 'height 0.3s ease',
        }}
      >
        {filteredLogs.length === 0 ? (
          <div style={{ color: '#52525B', fontStyle: 'italic', padding: 20, textAlign: 'center' }}>
            [ Waiting for pipeline telemetry output... ]
          </div>
        ) : (
          filteredLogs.map((log, idx) => {
            const style = getLevelStyle(log.level);
            return (
              <motion.div
                key={idx}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2 }}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 12,
                  marginBottom: 6,
                  padding: '3px 6px',
                  borderRadius: 4,
                  background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                }}
              >
                {/* Line Index */}
                <span style={{ color: '#3F3F46', width: 28, flexShrink: 0, textAlign: 'right', userSelect: 'none' }}>
                  {(idx + 1).toString().padStart(2, '0')}
                </span>

                {/* Timestamp */}
                <span style={{ color: '#71717A', flexShrink: 0, userSelect: 'none' }}>
                  {log.timestamp}
                </span>

                {/* Stage Badge */}
                <span
                  style={{
                    padding: '1px 6px',
                    borderRadius: 4,
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    color: '#D4D4D8',
                    fontSize: 10,
                    fontWeight: 700,
                    flexShrink: 0,
                  }}
                >
                  {log.stage}
                </span>

                {/* Level Badge */}
                <span
                  style={{
                    padding: '1px 6px',
                    borderRadius: 4,
                    background: style.bg,
                    border: `1px solid ${style.border}`,
                    color: style.color,
                    fontSize: 10,
                    fontWeight: 700,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 4,
                    flexShrink: 0,
                  }}
                >
                  <span>{style.icon}</span>
                  <span>{log.level}</span>
                </span>

                {/* Log Message */}
                <span style={{ color: '#F4F4F6', wordBreak: 'break-word', flexGrow: 1 }}>
                  {log.message}
                  {log.details && (
                    <span style={{ display: 'block', color: '#A1A1AA', fontSize: 11, marginTop: 2, fontStyle: 'italic' }}>
                      ↳ {log.details}
                    </span>
                  )}
                </span>
              </motion.div>
            );
          })
        )}
        <div ref={logEndRef} />
      </div>
    </motion.div>
  );
}
