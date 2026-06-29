'use client';

import React from 'react';
import type { TaskStatus } from '@/lib/api';
import { STAGE_LABELS } from '@/lib/api';

interface Stage {
  key: TaskStatus;
  label: string;
  icon: React.ReactNode;
  description: string;
}

const STAGES: Stage[] = [
  {
    key: 'extracting',
    label: 'Extracting PE Features',
    icon: <PEIcon />,
    description: 'Parsing headers, sections, imports, exports',
  },
  {
    key: 'static_analysis',
    label: 'Static Analysis',
    icon: <StaticIcon />,
    description: 'Entropy, strings, opcodes, YARA rules',
  },
  {
    key: 'sandbox',
    label: 'Sandbox Execution',
    icon: <SandboxIcon />,
    description: 'Behavioral profiling in isolated VM',
  },
  {
    key: 'ml_classification',
    label: 'ML Classification',
    icon: <MLIcon />,
    description: 'Random Forest + LSTM ensemble scoring',
  },
  {
    key: 'deception',
    label: 'Deception Layer',
    icon: <DeceptionIcon />,
    description: 'Honeypots active, data sinkholed',
  },
  {
    key: 'reporting',
    label: 'Forensic Report',
    icon: <ReportIcon />,
    description: 'Compiling SHAP features + timeline',
  },
];

const STAGE_ORDER: TaskStatus[] = [
  'pending',
  'extracting',
  'static_analysis',
  'sandbox',
  'ml_classification',
  'deception',
  'reporting',
  'complete',
];

type StageState = 'done' | 'active' | 'pending';

function getStageState(stageKey: TaskStatus, currentStatus: TaskStatus): StageState {
  const currentIdx = STAGE_ORDER.indexOf(currentStatus);
  const stageIdx = STAGE_ORDER.indexOf(stageKey);
  if (stageIdx < currentIdx) return 'done';
  if (stageIdx === currentIdx) return 'active';
  return 'pending';
}

interface ProgressPipelineProps {
  status: TaskStatus;
  progress: number;
  message?: string;
  elapsedSeconds?: number;
}

export default function ProgressPipeline({
  status,
  progress,
  message,
  elapsedSeconds,
}: ProgressPipelineProps) {
  const isFailed = status === 'failed';
  const isComplete = status === 'complete';

  return (
    <div
      className="glass-card animate-fade-in-up"
      style={{ padding: '32px 28px', width: '100%' }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 28,
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {isFailed ? (
            <ErrorSpinner />
          ) : isComplete ? (
            <CheckmarkIcon />
          ) : (
            <SpinnerRings />
          )}
          <div>
            <p
              style={{
                color: isFailed
                  ? '#ff3366'
                  : isComplete
                  ? '#00ff88'
                  : 'rgba(255,255,255,0.85)',
                fontWeight: 600,
                fontSize: 15,
                marginBottom: 2,
              }}
            >
              {isFailed
                ? 'Analysis Failed'
                : isComplete
                ? 'Analysis Complete'
                : STAGE_LABELS[status] ?? 'Analyzing…'}
            </p>
            {message && (
              <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: 12 }}>{message}</p>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {/* Overall progress */}
          <div style={{ textAlign: 'right' }}>
            <p
              style={{
                color: '#6366f1',
                fontWeight: 700,
                fontSize: 22,
                lineHeight: 1,
                fontFamily: "'JetBrains Mono', monospace",
              }}
            >
              {progress}%
            </p>
            {elapsedSeconds !== undefined && (
              <p style={{ color: 'rgba(255,255,255,0.3)', fontSize: 11, marginTop: 2 }}>
                {elapsedSeconds.toFixed(0)}s elapsed
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Overall progress bar */}
      <div className="progress-bar" style={{ marginBottom: 28, height: 4 }}>
        <div
          className="progress-bar-fill"
          style={{
            width: `${progress}%`,
            background: isFailed
              ? 'linear-gradient(90deg, #ff3366, #ff6688)'
              : isComplete
              ? 'linear-gradient(90deg, #00ff88, #00ffaa)'
              : 'linear-gradient(90deg, #6366f1, #818cf8)',
            transition: 'width 0.6s cubic-bezier(0.16, 1, 0.3, 1)',
          }}
        />
      </div>

      {/* Stage list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {STAGES.map((stage, idx) => {
          const state = getStageState(stage.key, status);
          return (
            <StageRow
              key={stage.key}
              stage={stage}
              state={isFailed && state === 'active' ? 'pending' : state}
              index={idx}
            />
          );
        })}
      </div>
    </div>
  );
}

// ─── Stage Row ────────────────────────────────────────────────────────────────

interface StageRowProps {
  stage: Stage;
  state: StageState;
  index: number;
}

function StageRow({ stage, state, index }: StageRowProps) {
  const color =
    state === 'done' ? '#00ff88' : state === 'active' ? '#6366f1' : 'rgba(255,255,255,0.15)';

  const bgColor =
    state === 'done'
      ? 'rgba(0,255,136,0.06)'
      : state === 'active'
      ? 'rgba(99,102,241,0.08)'
      : 'transparent';

  return (
    <div
      className={`animate-fade-in-up stagger-${index + 1}`}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 14,
        padding: '12px 14px',
        borderRadius: 10,
        background: bgColor,
        border: `1px solid ${state === 'active' ? 'rgba(99,102,241,0.2)' : 'transparent'}`,
        transition: 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
      }}
    >
      {/* Stage icon */}
      <div
        style={{
          width: 36,
          height: 36,
          borderRadius: 8,
          background:
            state === 'done'
              ? 'rgba(0,255,136,0.12)'
              : state === 'active'
              ? 'rgba(99,102,241,0.15)'
              : 'rgba(255,255,255,0.04)',
          border: `1px solid ${color}40`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          transition: 'all 0.4s ease',
          color: color,
        }}
      >
        {state === 'active' ? <PulsingDot color={color} /> : stage.icon}
      </div>

      {/* Label + description */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <p
          style={{
            fontWeight: 500,
            fontSize: 13,
            color:
              state === 'done'
                ? 'rgba(255,255,255,0.85)'
                : state === 'active'
                ? 'rgba(255,255,255,0.95)'
                : 'rgba(255,255,255,0.3)',
            marginBottom: 2,
            transition: 'color 0.3s ease',
          }}
        >
          {stage.label}
        </p>
        <p
          style={{
            fontSize: 11,
            color:
              state === 'active' ? 'rgba(255,255,255,0.45)' : 'rgba(255,255,255,0.2)',
            transition: 'color 0.3s ease',
          }}
        >
          {stage.description}
        </p>
      </div>

      {/* Status badge */}
      <div style={{ flexShrink: 0 }}>
        {state === 'done' && (
          <span className="badge badge-green">
            <svg width="7" height="7" viewBox="0 0 7 7" fill="none">
              <path d="M1 3.5L2.8 5.5L6 1.5" stroke="#00ff88" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Done
          </span>
        )}
        {state === 'active' && (
          <span className="badge badge-blue" style={{ animation: 'pulse-glow-blue 2s infinite' }}>
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: '#6366f1',
                display: 'inline-block',
                animation: 'ping-subtle 1.2s ease-out infinite',
              }}
            />
            Active
          </span>
        )}
        {state === 'pending' && (
          <span
            style={{
              fontSize: 11,
              color: 'rgba(255,255,255,0.2)',
              fontWeight: 500,
            }}
          >
            Waiting
          </span>
        )}
      </div>
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SpinnerRings() {
  return (
    <div style={{ position: 'relative', width: 28, height: 28, flexShrink: 0 }}>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '50%',
          border: '2px solid transparent',
          borderTopColor: '#6366f1',
          animation: 'spin-ring 0.9s linear infinite',
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: 5,
          borderRadius: '50%',
          border: '1.5px solid transparent',
          borderBottomColor: '#818cf8',
          animation: 'spin-ring-reverse 1.4s linear infinite',
        }}
      />
    </div>
  );
}

function CheckmarkIcon() {
  return (
    <div
      style={{
        width: 28,
        height: 28,
        borderRadius: '50%',
        background: 'rgba(0,255,136,0.15)',
        border: '1.5px solid rgba(0,255,136,0.4)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        boxShadow: '0 0 16px rgba(0,255,136,0.3)',
      }}
    >
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
        <path
          d="M2.5 7L5.5 10L11.5 4"
          stroke="#00ff88"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

function ErrorSpinner() {
  return (
    <div
      style={{
        width: 28,
        height: 28,
        borderRadius: '50%',
        background: 'rgba(255,51,102,0.15)',
        border: '1.5px solid rgba(255,51,102,0.4)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
      }}
    >
      <span style={{ color: '#ff3366', fontSize: 14, fontWeight: 700 }}>✕</span>
    </div>
  );
}

function PulsingDot({ color }: { color: string }) {
  return (
    <div style={{ position: 'relative', width: 10, height: 10 }}>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '50%',
          background: color,
          opacity: 0.3,
          animation: 'ping-subtle 1.2s ease-out infinite',
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: 2,
          borderRadius: '50%',
          background: color,
        }}
      />
    </div>
  );
}

// ─── Stage Icons ─────────────────────────────────────────────────────────────

function PEIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <rect x="2" y="1" width="9" height="11" rx="1" stroke="currentColor" strokeWidth="1.2" />
      <path d="M11 1l3 3v10H6" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      <path d="M4 6h5M4 8h3" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" />
    </svg>
  );
}

function StaticIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M2 4h12M2 8h8M2 12h10" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      <circle cx="13" cy="12" r="2" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}

function SandboxIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <rect x="1" y="4" width="14" height="9" rx="1" stroke="currentColor" strokeWidth="1.2" />
      <path d="M5 4V3a3 3 0 016 0v1" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="8" cy="8.5" r="1.5" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}

function MLIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="2.5" cy="4" r="1.2" stroke="currentColor" strokeWidth="1" />
      <circle cx="13.5" cy="4" r="1.2" stroke="currentColor" strokeWidth="1" />
      <circle cx="2.5" cy="12" r="1.2" stroke="currentColor" strokeWidth="1" />
      <circle cx="13.5" cy="12" r="1.2" stroke="currentColor" strokeWidth="1" />
      <path d="M3.6 4.5L6 6.5M12.4 4.5L10 6.5M3.6 11.5L6 9.5M12.4 11.5L10 9.5" stroke="currentColor" strokeWidth="1" strokeLinecap="round" />
    </svg>
  );
}

function DeceptionIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path d="M8 2L3 4.5v4C3 11.5 5.5 14 8 14c2.5 0 5-2.5 5-5.5v-4L8 2z" stroke="currentColor" strokeWidth="1.2" />
      <path d="M6 8l1.5 1.5L10 6" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ReportIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <rect x="3" y="1" width="10" height="14" rx="1.5" stroke="currentColor" strokeWidth="1.2" />
      <path d="M5.5 5h5M5.5 7.5h5M5.5 10h3" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" />
    </svg>
  );
}
