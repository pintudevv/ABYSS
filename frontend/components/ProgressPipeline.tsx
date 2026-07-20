'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { TaskStatus, TelemetryLog } from '@/lib/api';
import { STAGE_LABELS } from '@/lib/api';
import TelemetryTerminal from './TelemetryTerminal';

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
  telemetryLogs?: TelemetryLog[];
}

export default function ProgressPipeline({
  status,
  progress,
  message,
  elapsedSeconds,
  telemetryLogs,
}: ProgressPipelineProps) {
  const isFailed = status === 'failed';
  const isComplete = status === 'complete';

  const containerVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        staggerChildren: 0.08,
        delayChildren: 0.2,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, x: -20 },
    visible: {
      opacity: 1,
      x: 0,
      transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] as const },
    },
  };

  return (
    <motion.div
      className="border border-zinc-200 bg-white"
      style={{ padding: '32px 28px', width: '100%' }}
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      role="region"
      aria-label="Analysis pipeline progress"
      aria-live="polite"
    >
      {/* Header */}
      <motion.div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 28,
          flexWrap: 'wrap',
          gap: 12,
        }}
        variants={itemVariants}
      >
        <motion.div
          style={{ display: 'flex', alignItems: 'center', gap: 10 }}
          variants={itemVariants}
        >
          <AnimatePresence mode="wait">
            {isFailed ? (
              <motion.div key="error" initial={{ opacity: 0, scale: 0.5, rotate: -90 }} animate={{ opacity: 1, scale: 1, rotate: 0 }} exit={{ opacity: 0, scale: 0.5, rotate: 90 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }} aria-hidden="true">
                <ErrorSpinner />
              </motion.div>
            ) : isComplete ? (
              <motion.div key="complete" initial={{ opacity: 0, scale: 0.5, rotate: 90 }} animate={{ opacity: 1, scale: 1, rotate: 0 }} exit={{ opacity: 0, scale: 0.5, rotate: -90 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }} aria-hidden="true">
                <CheckmarkIcon />
              </motion.div>
            ) : (
              <motion.div key="loading" initial={{ opacity: 0, scale: 0.5 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.5 }} transition={{ type: 'spring', stiffness: 300, damping: 20 }} aria-hidden="true">
                <SpinnerRings />
              </motion.div>
            )}
          </AnimatePresence>
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            variants={itemVariants}
          >
            <motion.p
              style={{
                color: isFailed ? '#EF4444' : isComplete ? '#10B981' : '#111111',
                fontWeight: 600,
                fontSize: 15,
                marginBottom: 2,
              }}
            >
              {isFailed ? 'Analysis Failed' : isComplete ? 'Analysis Complete' : STAGE_LABELS[status] ?? 'Analyzing…'}
            </motion.p>
            {message && (
              <motion.p
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.15 }}
                style={{ color: 'rgba(0,0,0,0.4)', fontSize: 12 }}
              >
                {message}
              </motion.p>
            )}
          </motion.div>
        </motion.div>

        <motion.div
          style={{ display: 'flex', alignItems: 'center', gap: 16 }}
          variants={itemVariants}
        >
          <motion.div
            style={{ textAlign: 'right' }}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
          >
            <motion.span
              style={{
                color: '#111111',
                fontWeight: 700,
                fontSize: 22,
                lineHeight: 1,
                fontFamily: "'JetBrains Mono', monospace",
              }}
            >
              <AnimatePresence mode="wait">
                <motion.span
                  key={progress}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.3 }}
                >
                  {progress}%
                </motion.span>
              </AnimatePresence>
            </motion.span>
            {elapsedSeconds !== undefined && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                style={{ color: 'rgba(0,0,0,0.3)', fontSize: 11, marginTop: 2 }}
              >
                {elapsedSeconds.toFixed(0)}s elapsed
              </motion.p>
            )}
          </motion.div>
        </motion.div>
      </motion.div>

      {/* Overall progress bar */}
      <motion.div
        style={{ marginBottom: 28, height: 6, background: '#E2E8F0', borderRadius: 999, overflow: 'hidden' }}
        variants={itemVariants}
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Analysis progress: ${progress}%`}
      >
        <motion.div
          className="progress-bar-fill"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          style={{
            background: isFailed
              ? '#EF4444'
              : isComplete
              ? '#10B981'
              : '#111111',
            borderRadius: '999px',
            height: '100%',
            transformOrigin: 'left center',
          }}
        />
      </motion.div>

      {/* Stage list */}
      <motion.div
        style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
        variants={itemVariants}
      >
        <AnimatePresence mode="popLayout">
          {STAGES.map((stage) => {
            const state = getStageState(stage.key, status);
            const adjustedState = isFailed && state === 'active' ? 'pending' : state;
            return (
              <StageRow
                key={stage.key}
                stage={stage}
                state={adjustedState}
              />
            );
          })}
        </AnimatePresence>
      </motion.div>

      {/* Live Telemetry Terminal Stream */}
      <TelemetryTerminal
        logs={telemetryLogs ?? []}
        isComplete={isComplete}
        isFailed={isFailed}
      />
    </motion.div>
  );
}

// ─── Stage Row ────────────────────────────────────────────────────────────────

interface StageRowProps {
  stage: Stage;
  state: StageState;
}

const stageRowVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] as const },
  },
  exit: { opacity: 0, x: 20, transition: { duration: 0.2 } },
};

function StageRow({ stage, state }: StageRowProps) {
  const color = state === 'done' ? '#00ff88' : state === 'active' ? '#6366f1' : 'rgba(255,255,255,0.15)';
  const bgColor = state === 'done' ? 'rgba(0,255,136,0.06)' : state === 'active' ? 'rgba(99,102,241,0.08)' : 'transparent';

  return (
    <motion.div
      variants={stageRowVariants}
      layout
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
      <AnimatePresence mode="wait">
        <motion.div
          key={state}
          initial={{ opacity: 0, scale: 0.5, rotate: state === 'done' ? 90 : state === 'active' ? -90 : 0 }}
          animate={{ opacity: 1, scale: 1, rotate: 0 }}
          exit={{ opacity: 0, scale: 0.5, rotate: state === 'done' ? -90 : state === 'active' ? 90 : 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 20 }}
          style={{
            width: 36,
            height: 36,
            borderRadius: 8,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            color: color,
          }}
          aria-hidden="true"
        >
          {state === 'active' ? <PulsingDot color={color} /> : stage.icon}
        </motion.div>
      </AnimatePresence>

      {/* Label + description */}
      <motion.div
        style={{ flex: 1, minWidth: 0 }}
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.05 }}
      >
        <motion.p
          style={{
            fontWeight: 500,
            fontSize: 13,
            color:
              state === 'done' ? 'rgba(255,255,255,0.85)'
              : state === 'active' ? 'rgba(255,255,255,0.95)'
              : 'rgba(255,255,255,0.3)',
            marginBottom: 2,
            transition: 'color 0.3s ease',
          }}
        >
          {stage.label}
        </motion.p>
        <motion.p
          style={{
            fontSize: 11,
            color: state === 'active' ? 'rgba(255,255,255,0.45)' : 'rgba(255,255,255,0.2)',
            transition: 'color 0.3s ease',
          }}
        >
          {stage.description}
        </motion.p>
      </motion.div>

      {/* Status badge */}
      <motion.div
        style={{ flexShrink: 0 }}
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.1 }}
      >
        <AnimatePresence mode="wait">
          {state === 'done' && (
            <motion.span
              key="done"
              className="badge badge-green"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ type: 'spring', stiffness: 300, damping: 20 }}
            >
              Complete
            </motion.span>
          )}
        </AnimatePresence>
      </motion.div>
    </motion.div>
  );
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function PEIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  );
}

function StaticIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  );
}

function SandboxIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="2" y="3" width="20" height="14" rx="2" />
      <path d="M8 21h8" />
      <path d="M12 17v4" />
    </svg>
  );
}

function MLIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
      <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
      <line x1="12" y1="22.08" x2="12" y2="12" />
    </svg>
  );
}

function DeceptionIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v6l4 2" />
      <path d="M12 6v6l-4 2" />
    </svg>
  );
}

function ReportIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  );
}

function SpinnerRings() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <circle
        cx="14"
        cy="14"
        r="12"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeDasharray="35"
        strokeDashoffset="35"
        strokeOpacity="0.2"
      />
      <motion.circle
        cx="14"
        cy="14"
        r="12"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeDasharray="35"
        style={{ opacity: 0.8 }}
        initial={{ strokeDashoffset: 35, pathLength: 0.5 }}
        animate={{ strokeDashoffset: 0, pathLength: 1 }}
        transition={{ duration: 1.2, ease: 'linear', repeat: Infinity }}
      />
    </svg>
  );
}

function CheckmarkIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <circle cx="14" cy="14" r="12" stroke="currentColor" strokeWidth="2.5" strokeOpacity="0.15" />
      <motion.path
        d="M8 14l4 4 8-8"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      />
    </svg>
  );
}

function ErrorSpinner() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <circle cx="14" cy="14" r="12" stroke="currentColor" strokeWidth="2.5" strokeOpacity="0.15" />
      <motion.path
        d="M14 7v7M14 16v.01"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        initial={{ opacity: 0, scale: 0.5 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 0.2 }}
      />
    </svg>
  );
}

function PulsingDot({ color }: { color: string }) {
  return (
    <motion.span
      style={{
        width: 10,
        height: 10,
        borderRadius: '50%',
        background: color,
        boxShadow: `0 0 12px ${color}`,
      }}
      animate={{ scale: [1, 1.3, 1], opacity: [1, 0.5, 1] }}
      transition={{ duration: 1, repeat: Infinity, ease: 'easeInOut' }}
      aria-hidden="true"
    />
  );
}