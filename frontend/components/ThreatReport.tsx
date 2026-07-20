'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { 
  FileText, Cpu, Archive, FileWarning, ShieldAlert, ShieldCheck, 
  Network, Database, Key, Settings, Activity, Globe, Shield 
} from 'lucide-react';
import type {
  ThreatReport,
  StolenFile,
  ExfilEndpoint,
  MockData,
  ApiHook,
  ShapFeature,
  TimelineEvent,
  TimelineEventType,
  SeverityLevel,
} from '@/lib/api';
import { formatFileSize, formatDuration } from '@/lib/api';
import CircularProgress from './CircularProgress';
import TelemetryTerminal from './TelemetryTerminal';

interface ThreatReportProps {
  report: ThreatReport;
  onDownload: () => void;
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
      delayChildren: 0.1,
    },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] as const },
  },
};

const itemVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.3, ease: [0.16, 1, 0.3, 1] as const },
  },
};

export default function ThreatReportView({ report, onDownload }: ThreatReportProps) {
  const threatColor = report.is_threat ? '#FF2E55' : '#00E599';
  const confidencePct = Math.round(report.confidence * 100);

  return (
    <motion.div
      style={{ display: 'flex', flexDirection: 'column', gap: 28 }}
      initial="hidden"
      animate="visible"
      variants={containerVariants}
    >
      {/* ── Hero Header ────────────────────────────────────────────────────── */}
      <motion.div
        style={{
          padding: '36px 32px',
          background: 'rgba(13, 13, 18, 0.85)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: 20,
          boxShadow: '0 20px 50px rgba(0,0,0,0.6)',
        }}
        variants={cardVariants}
      >
        <motion.div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 24,
            flexWrap: 'wrap',
          }}
          variants={itemVariants}
        >
          {/* Left: file info + threat verdict */}
          <motion.div
            style={{ flex: 1, minWidth: 260 }}
            variants={itemVariants}
          >
            {/* Filename */}
            <motion.div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                marginBottom: 6,
              }}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 }}
            >
              <motion.span
                style={{ fontSize: 18, opacity: 0.8, display: 'inline-flex', alignItems: 'center', color: '#F4F4F6' }}
                initial={{ scale: 0.5, rotate: -180 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{ type: 'spring', stiffness: 260, damping: 20, delay: 0.15 }}
              >
                {getFileIcon(report.file_type)}
              </motion.span>
              <motion.p
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 15,
                  color: '#F4F4F6',
                  wordBreak: 'break-all',
                  fontWeight: 700,
                }}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
              >
                {report.filename}
              </motion.p>
            </motion.div>

            {/* Meta badges */}
            <motion.div
              style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 24 }}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25, staggerChildren: 0.05 }}
            >
              <motion.span style={{ fontSize: 11, color: '#A1A1AA', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.04)', padding: '4px 10px' }}>
                {formatFileSize(report.file_size)}
              </motion.span>
              <motion.span style={{ fontSize: 11, color: '#A1A1AA', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.04)', padding: '4px 10px' }}>
                {formatDuration(report.analysis_duration_seconds)}
              </motion.span>
              <motion.span
                style={{ fontSize: 11, fontFamily: "'JetBrains Mono', monospace", color: '#71717A', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.04)', padding: '4px 10px' }}
              >
                SHA256: {report.sha256?.slice(0, 16) ?? 'N/A'}…
              </motion.span>
            </motion.div>

            {/* HUGE threat badge */}
            <motion.div
              style={{ marginBottom: 16 }}
              initial={{ opacity: 0, scale: 0.9, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              transition={{ delay: 0.35, type: 'spring', stiffness: 200, damping: 18 }}
            >
              <motion.div
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: '12px 24px',
                  borderRadius: 12,
                  background: report.is_threat ? 'rgba(255,46,85,0.12)' : 'rgba(0,229,153,0.12)',
                  border: `1px solid ${report.is_threat ? 'rgba(255,46,85,0.4)' : 'rgba(0,229,153,0.4)'}`,
                  boxShadow: report.is_threat ? '0 0 30px rgba(255,46,85,0.2)' : '0 0 30px rgba(0,229,153,0.2)',
                }}
              >
                <motion.span
                  style={{ display: 'inline-flex', alignItems: 'center' }}
                  initial={{ opacity: 0, scale: 0, rotate: -90 }}
                  animate={{ opacity: 1, scale: 1, rotate: 0 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 0.4 }}
                >
                  {report.is_threat ? (
                    <ShieldAlert className="w-5 h-5 text-[#FF2E55]" />
                  ) : (
                    <ShieldCheck className="w-5 h-5 text-[#00E599]" />
                  )}
                </motion.span>
                <motion.span
                  style={{
                    fontSize: 16,
                    fontWeight: 800,
                    letterSpacing: '0.04em',
                    fontFamily: "'JetBrains Mono', monospace",
                    color: threatColor,
                  }}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.45 }}
                >
                  {report.is_threat ? 'THREAT DETECTED' : 'FILE CLEAN'}
                </motion.span>
              </motion.div>
            </motion.div>

            {/* Threat type + zero-day */}
            <motion.div
              style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, staggerChildren: 0.05 }}
            >
              {report.is_threat && (
                <motion.span
                  style={{
                    background: 'rgba(255,46,85,0.18)',
                    color: '#FF2E55',
                    border: '1px solid rgba(255,46,85,0.4)',
                    borderRadius: 6,
                    fontSize: 11,
                    fontFamily: "'JetBrains Mono', monospace",
                    fontWeight: 700,
                    padding: '5px 14px',
                    textTransform: 'uppercase',
                  }}
                  initial={{ scale: 0.8 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                >
                  {report.threat_type}
                </motion.span>
              )}
              {report.is_zero_day && (
                <motion.span
                  className="badge animate-pulse"
                  style={{
                    background: 'rgba(255,170,0,0.15)',
                    color: '#ffaa00',
                    border: '1px solid rgba(255,170,0,0.3)',
                    fontSize: 11,
                    padding: '5px 12px',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 6,
                  }}
                  initial={{ scale: 0.8 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                >
                  <Activity className="w-3.5 h-3.5" /> ZERO-DAY
                </motion.span>
              )}
              <motion.span
                style={{
                  fontSize: 12,
                  color: '#A1A1AA',
                  padding: '4px 0',
                }}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.55 }}
              >
                Risk Score:{' '}
                <motion.span
                  style={{ color: getRiskColor(report.risk_score), fontWeight: 700 }}
                  initial={{ opacity: 0, scale: 0.5 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 0.6 }}
                >
                  {report.risk_score}/100
                </motion.span>
              </motion.span>
            </motion.div>
          </motion.div>

          {/* Right: Circular confidence meter */}
          <motion.div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 8,
            }}
            variants={itemVariants}
          >
            <CircularProgress
              value={confidencePct}
              size={140}
              strokeWidth={8}
              color={threatColor}
              label="Confidence"
              sublabel="ML Score"
            />
            <motion.p
              style={{ fontSize: 11, color: '#A1A1AA', textAlign: 'center' }}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 }}
            >
              Hybrid ML Ensemble
            </motion.p>
          </motion.div>
        </motion.div>
      </motion.div>

      {/* ── 4 Evidence Cards ───────────────────────────────────────────────── */}
      <motion.div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: 20,
        }}
        variants={containerVariants}
      >
        <StolenFilesCard files={report.stolen_files} />
        <ExfilCard endpoints={report.exfil_endpoints} />
        <MockDataCard mocks={report.mock_data_served} />
        <ApiHooksCard hooks={report.api_hooks} />
      </motion.div>

      {/* ── SHAP Feature Importance ─────────────────────────────────────────── */}
      <ShapChart features={report.shap_features} />

      {/* ── Attack Timeline ─────────────────────────────────────────────────── */}
      <AttackTimeline events={report.timeline} />

      {/* ── Real-Time Terminal Telemetry Stream ───────────────────────────── */}
      <TelemetryTerminal
        logs={
          report.telemetry_logs?.length
            ? report.telemetry_logs
            : report.timeline?.map((e) => ({
                timestamp: e.timestamp,
                stage: e.type.toUpperCase(),
                level: (e.severity === 'critical' || e.severity === 'high' ? 'BLOCK' : e.type === 'process' ? 'HOOK' : 'INFO') as any,
                message: e.description,
                details: e.details,
              })) ?? []
        }
        isComplete={true}
      />

      {/* ── Bottom Verdict ──────────────────────────────────────────────────── */}
      <VerdictFooter
        isThreat={report.is_threat}
        verdictMessage={report.verdict_message}
        onDownload={onDownload}
      />
    </motion.div>
  );
}

// ─── Report Header ────────────────────────────────────────────────────────────

// ─── Stolen Files Card ────────────────────────────────────────────────────────

function StolenFilesCard({ files }: { files: StolenFile[] }) {
  const safeFiles = files ?? [];
  return (
    <EvidenceCard
      title="Data It Tried to Steal"
      icon={<Archive className="w-4 h-4 text-[#ff3366]" />}
      accentColor="#ff3366"
      count={safeFiles.length}
    >
      {safeFiles.length === 0 ? (
        <EmptyState text="No file access attempts recorded" />
      ) : (
        <motion.div
          style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
          variants={containerVariants}
        >
          {safeFiles.map((f, i) => (
            <motion.div
              key={i}
              style={listItemStyle}
              variants={itemVariants}
            >
              <motion.div
                style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 }}
              >
                <motion.span
                  style={{ display: 'inline-flex', alignItems: 'center', opacity: 0.7 }}
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 0.15 }}
                >
                  {getFileTypeIcon(f.type)}
                </motion.span>
                <motion.span
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 11,
                    color: '#F4F4F6',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    fontWeight: 500,
                  }}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 }}
                >
                  {f.path}
                </motion.span>
              </motion.div>
              {f.blocked && (
                <motion.span
                  className="badge badge-red"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 0.25 }}
                >
                  BLOCKED
                </motion.span>
              )}
            </motion.div>
          ))}
        </motion.div>
      )}
    </EvidenceCard>
  );
}

// ─── Exfil Endpoints Card ─────────────────────────────────────────────────────

function ExfilCard({ endpoints }: { endpoints: ExfilEndpoint[] }) {
  const safeEndpoints = endpoints ?? [];
  return (
    <EvidenceCard
      title="Where It Tried to Send It"
      icon={<Globe className="w-4 h-4 text-[#ff3366]" />}
      accentColor="#ff3366"
      count={safeEndpoints.length}
    >
      {safeEndpoints.length === 0 ? (
        <EmptyState text="No exfiltration attempts detected" />
      ) : (
        <motion.div
          style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
          variants={containerVariants}
        >
          {safeEndpoints.map((ep, i) => (
            <motion.div
              key={i}
              style={listItemStyle}
              variants={itemVariants}
            >
              <motion.div
                style={{ minWidth: 0 }}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 }}
              >
                <motion.div
                  style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 }}
                >
                  <motion.span
                    style={{ display: 'inline-flex', alignItems: 'center' }}
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 0.15 }}
                  >
                    {ep.country_flag && ep.country_flag !== '🌐' ? (
                      <span className="text-base">{ep.country_flag}</span>
                    ) : (
                      <Globe className="w-4 h-4 text-indigo-400" />
                    )}
                  </motion.span>
                  <motion.span
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 11,
                      color: '#EF4444',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      fontWeight: 600,
                    }}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 }}
                  >
                    {ep.domain || ep.ip}:{ep.port}
                  </motion.span>
                </motion.div>
                <motion.p
                  style={{ fontSize: 10, color: '#A1A1AA', marginTop: 1 }}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.25 }}
                >
                  {ep.protocol} · {ep.country}
                </motion.p>
              </motion.div>
              {ep.sinkholed && (
                <motion.span
                  className="badge badge-amber"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 0.3 }}
                >
                  SINKHOLED
                </motion.span>
              )}
            </motion.div>
          ))}
        </motion.div>
      )}
    </EvidenceCard>
  );
}

// ─── Mock Data Card ───────────────────────────────────────────────────────────

function MockDataCard({ mocks }: { mocks: MockData[] }) {
  const safeMocks = mocks ?? [];
  return (
    <EvidenceCard
      title="What We Gave It Instead"
      icon={<ShieldCheck className="w-4 h-4 text-[#6366f1]" />}
      accentColor="#6366f1"
      count={safeMocks.length}
    >
      {safeMocks.length === 0 ? (
        <EmptyState text="No mock data required" />
      ) : (
        <motion.div
          style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
          variants={containerVariants}
        >
          {safeMocks.map((m, i) => (
            <motion.div
              key={i}
              style={listItemStyle}
              variants={itemVariants}
            >
              <motion.div
                style={{ minWidth: 0 }}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 }}
              >
                <motion.p
                  style={{ fontSize: 12, color: '#F4F4F6', marginBottom: 2, fontWeight: 550 }}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 }}
                >
                  {m.mock_description}
                </motion.p>
                <motion.p
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 10,
                    color: '#A1A1AA',
                  }}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 }}
                >
                  Served at: {m.served_at}
                </motion.p>
              </motion.div>
              <motion.span
                className="badge badge-blue"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 0.25 }}
              >
                MOCK
              </motion.span>
            </motion.div>
          ))}
        </motion.div>
      )}
    </EvidenceCard>
  );
}

// ─── API Hooks Card ───────────────────────────────────────────────────────────

function ApiHooksCard({ hooks }: { hooks: ApiHook[] }) {
  const safeHooks = hooks ?? [];
  return (
    <EvidenceCard
      title="API Hooks Triggered"
      icon={<Activity className="w-4 h-4 text-[#22d3ee]" />}
      accentColor="#22d3ee"
      count={safeHooks.length}
    >
      {safeHooks.length === 0 ? (
        <EmptyState text="No suspicious API calls detected" />
      ) : (
        <motion.div
          style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
          variants={containerVariants}
        >
          {safeHooks.map((h, i) => (
            <motion.div
              key={i}
              style={listItemStyle}
              variants={itemVariants}
            >
              <motion.div
                style={{ minWidth: 0 }}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 }}
              >
                <motion.div
                  style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 }}
                >
                  <motion.span
                    className={`badge ${getSeverityBadgeClass(h.severity)}`}
                    style={{ fontSize: 9, padding: '2px 7px' }}
                    initial={{ scale: 0.8 }}
                    animate={{ scale: 1 }}
                    transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 0.15 }}
                  >
                    {h.severity.toUpperCase()}
                  </motion.span>
                  <motion.span
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 11,
                      color: '#F4F4F6',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      fontWeight: 600,
                    }}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 }}
                  >
                    {h.function_name}
                  </motion.span>
                </motion.div>
                <motion.p
                  style={{ fontSize: 10, color: '#A1A1AA', marginTop: 2 }}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.25 }}
                >
                  {h.module} · Called ×{h.call_count}
                </motion.p>
              </motion.div>
            </motion.div>
          ))}
        </motion.div>
      )}
    </EvidenceCard>
  );
}

// ─── Evidence Card Wrapper ────────────────────────────────────────────────────

function EvidenceCard({
  title,
  icon,
  accentColor,
  count,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  accentColor: string;
  count: number;
  children: React.ReactNode;
}) {
  return (
    <motion.div
      style={{
        padding: '24px 20px',
        background: 'rgba(13, 13, 18, 0.85)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: 16,
        boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
      }}
      variants={cardVariants}
      whileHover={{ y: -4, borderColor: 'rgba(255,255,255,0.18)', boxShadow: '0 24px 60px rgba(0,0,0,0.7)' }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
    >
      {/* Card header */}
      <motion.div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 16,
        }}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <motion.div
          style={{ display: 'flex', alignItems: 'center', gap: 8 }}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
        >
          <motion.span
            style={{ display: 'inline-flex', alignItems: 'center', opacity: 0.8, color: '#F4F4F6' }}
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 0.15 }}
          >
            {icon}
          </motion.span>
          <motion.h3
            style={{
              fontSize: 12,
              fontWeight: 700,
              letterSpacing: '0.07em',
              textTransform: 'uppercase',
              color: '#F4F4F6',
            }}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
          >
            {title}
          </motion.h3>
        </motion.div>
        <motion.span
          style={{
            fontSize: 13,
            fontWeight: 700,
            color: count > 0 ? '#141413' : '#9C978C',
            fontFamily: "'JetBrains Mono', monospace",
          }}
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 0.25 }}
        >
          {count}
        </motion.span>
      </motion.div>

      {/* Divider */}
      <motion.div
        style={{
          height: 1,
          background: 'rgba(255,255,255,0.08)',
          marginBottom: 14,
        }}
        initial={{ opacity: 0, scaleX: 0 }}
        animate={{ opacity: 1, scaleX: 1 }}
        transition={{ delay: 0.3, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      />

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
      >
        {children}
      </motion.div>
    </motion.div>
  );
}

// ─── SHAP Feature Chart ───────────────────────────────────────────────────────

function ShapChart({ features }: { features: ShapFeature[] }) {
  const safeFeatures = features ?? [];
  if (safeFeatures.length === 0) return null;

  const maxImpact = Math.max(...safeFeatures.map((f) => Math.abs(f.impact)));
  const sorted = [...safeFeatures].sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact)).slice(0, 10);

  return (
    <motion.div
      style={{ padding: "28px 24px", background: "rgba(13, 13, 18, 0.85)", backdropFilter: "blur(16px)", border: "1px solid rgba(255, 255, 255, 0.08)", borderRadius: 16, boxShadow: "0 20px 50px rgba(0,0,0,0.5)" }}
      variants={cardVariants}
    >
      <motion.div
        style={{ marginBottom: 20 }}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <motion.h3
          style={{
            fontSize: 12,
            fontWeight: 700,
            letterSpacing: '0.07em',
            textTransform: 'uppercase',
            color: '#F4F4F6',
            marginBottom: 4,
          }}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
        >
          SHAP Feature Importance
        </motion.h3>
        <motion.p
          style={{ fontSize: 12, color: '#A1A1AA' }}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
        >
          Top features influencing the ML classification decision
        </motion.p>
      </motion.div>

      <motion.div
        style={{ display: 'flex', flexDirection: 'column', gap: 10 }}
        variants={containerVariants}
      >
        {sorted.map((feature, i) => {
          const pct = (Math.abs(feature.impact) / maxImpact) * 100;
          const color = feature.direction === 'positive' ? '#ff3366' : '#6366f1';
          return (
            <motion.div
              key={i}
              className="stagger-in"
              style={{ display: 'flex', alignItems: 'center', gap: 12 }}
              variants={itemVariants}
            >
              {/* Feature name */}
              <motion.div
                style={{ width: 200, flexShrink: 0 }}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 }}
              >
                <motion.p
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 11,
                    color: '#F4F4F6',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                  title={feature.name}
                >
                  {feature.name}
                </motion.p>
                <motion.p
                  style={{ fontSize: 10, color: '#A1A1AA', marginTop: 1 }}
                >
                  val: {feature.value}
                </motion.p>
              </motion.div>

              {/* Bar */}
              <motion.div
                style={{ flex: 1, position: 'relative', height: 24 }}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.15 }}
              >
                <motion.div
                  style={{
                    position: 'absolute',
                    inset: 0,
                    borderRadius: 4,
                    background: 'rgba(255, 255, 255, 0.06)',
                  }}
                />
                <motion.div
                  className="shap-bar"
                  style={{
                    position: 'absolute',
                    left: 0,
                    top: 0,
                    bottom: 0,
                    width: 0,
                    borderRadius: 4,
                    background: color,
                  }}
                  animate={{ width: `${pct}%` }}
                  transition={{ delay: i * 0.08 + 0.2, duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                />
                <motion.div
                  style={{
                    position: 'absolute',
                    right: 8,
                    top: 0,
                    bottom: 0,
                    display: 'flex',
                    alignItems: 'center',
                  }}
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 }}
                >
                  <motion.span
                    style={{
                      fontSize: 10,
                      fontFamily: "'JetBrains Mono', monospace",
                      color: '#A1A1AA',
                    }}
                  >
                    {feature.impact.toFixed(3)}
                  </motion.span>
                </motion.div>
              </motion.div>

              {/* Direction badge */}
              <motion.span
                className={`badge ${feature.direction === 'positive' ? 'badge-red' : 'badge-blue'}`}
                style={{ fontSize: 9, padding: '2px 8px', flexShrink: 0 }}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 0.35 }}
              >
                {feature.direction === 'positive' ? '▲ MAL' : '▼ BEN'}
              </motion.span>
            </motion.div>
          );
        })}
      </motion.div>
    </motion.div>
  );
}

// ─── Attack Timeline ──────────────────────────────────────────────────────────

function AttackTimeline({ events }: { events: TimelineEvent[] }) {
  const safeEvents = events ?? [];
  if (safeEvents.length === 0) return null;

  const sorted = [...safeEvents].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  );

  return (
    <motion.div
      style={{ padding: "28px 24px", background: "rgba(13, 13, 18, 0.85)", backdropFilter: "blur(16px)", border: "1px solid rgba(255, 255, 255, 0.08)", borderRadius: 16, boxShadow: "0 20px 50px rgba(0,0,0,0.5)" }}
      variants={cardVariants}
    >
      <motion.div
        style={{ marginBottom: 24 }}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <motion.h3
          style={{
            fontSize: 12,
            fontWeight: 700,
            letterSpacing: '0.07em',
            textTransform: 'uppercase',
            color: '#F4F4F6',
            marginBottom: 4,
          }}
        >
          Attack Timeline
        </motion.h3>
        <motion.p
          style={{ fontSize: 12, color: '#A1A1AA' }}
        >
          {sorted.length} events recorded during sandbox execution
        </motion.p>
      </motion.div>

      <motion.div
        style={{ position: 'relative', paddingLeft: 40 }}
        variants={containerVariants}
      >
        {/* Vertical line */}
        <motion.div
          className="timeline-line"
          initial={{ scaleY: 0 }}
          animate={{ scaleY: 1 }}
          transition={{ delay: 0.3, duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          style={{ transformOrigin: 'top center' }}
        />

        <motion.div
          style={{ display: 'flex', flexDirection: 'column', gap: 16 }}
          variants={containerVariants}
        >
          {sorted.map((event, i) => (
            <TimelineItem
              key={i}
              event={event}
              index={i}
            />
          ))}
        </motion.div>
      </motion.div>
    </motion.div>
  );
}

function TimelineItem({
  event,
  index,
}: {
  event: TimelineEvent;
  index: number;
}) {
  const color = getSeverityColor(event.severity);

  return (
    <motion.div
      className="stagger-in"
      style={{ display: 'flex', alignItems: 'flex-start', gap: 12, position: 'relative' }}
      variants={itemVariants}
    >
      {/* Dot */}
      <motion.div
        style={{
          position: 'absolute',
          left: -40,
          top: 2,
          width: 20,
          height: 20,
          borderRadius: '50%',
          background: `${color}18`,
          border: `1.5px solid ${color}50`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          fontSize: 9,
        }}
        initial={{ opacity: 0, scale: 0 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: 'spring', stiffness: 300, damping: 20, delay: index * 0.08 + 0.2 }}
      >
        {getEventTypeIcon(event.type)}
      </motion.div>

      {/* Content */}
      <motion.div
        style={{ flex: 1 }}
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: index * 0.08 + 0.25 }}
      >
        <motion.div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 8,
            flexWrap: 'wrap',
          }}
        >
          <motion.p
            style={{ fontSize: 13, color: '#F4F4F6', lineHeight: 1.4, flex: 1 }}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
          >
            {event.description}
          </motion.p>
          <motion.span
            className={`badge ${getSeverityBadgeClass(event.severity)}`}
            style={{ fontSize: 9, padding: '2px 8px', flexShrink: 0 }}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 0.15 }}
          >
            {event.severity.toUpperCase()}
          </motion.span>
        </motion.div>
        <motion.div
          style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 4 }}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
        >
          <motion.span
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10,
              color: '#A1A1AA',
            }}
          >
            {formatTimestamp(event.timestamp)}
          </motion.span>
          <motion.span
            style={{
              fontSize: 10,
              color,
              textTransform: 'capitalize',
            }}
          >
            {event.type}
          </motion.span>
        </motion.div>
        {event.details && (
          <motion.p
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10,
              color: '#A1A1AA',
              marginTop: 4,
              background: 'rgba(255, 255, 255, 0.06)',
              padding: '4px 8px',
              borderRadius: 0,
              border: '1px solid #e4e4e7',
            }}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            {event.details}
          </motion.p>
        )}
      </motion.div>
    </motion.div>
  );
}

// ─── Verdict Footer ───────────────────────────────────────────────────────────

function VerdictFooter({
  isThreat,
  verdictMessage,
  onDownload,
}: {
  isThreat: boolean;
  verdictMessage: string;
  onDownload: () => void;
}) {
  const primaryColor = isThreat ? '#FF2E55' : '#00E599';
  return (
    <motion.div
      style={{
        padding: '28px 24px',
        borderRadius: 16,
        border: `1px solid ${isThreat ? 'rgba(255,46,85,0.4)' : 'rgba(0,229,153,0.4)'}`,
        background: isThreat ? 'rgba(255,46,85,0.08)' : 'rgba(0,229,153,0.08)',
        backdropFilter: 'blur(20px)',
        boxShadow: isThreat ? '0 0 35px rgba(255,46,85,0.15)' : '0 0 35px rgba(0,229,153,0.15)',
      }}
      variants={cardVariants}
    >
      <motion.div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 20,
          flexWrap: 'wrap',
        }}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <motion.div
          style={{ display: 'flex', alignItems: 'center', gap: 12 }}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
        >
          <motion.div
            style={{
              width: 40,
              height: 40,
              borderRadius: 0,
              background: isThreat ? 'rgba(158,42,43,0.1)' : 'rgba(45,95,62,0.1)',
              border: `1px solid ${isThreat ? '#9E2A2B' : '#2D5F3E'}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
            initial={{ scale: 0, rotate: -180 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 0.15 }}
            whileHover={{ scale: 1.05, rotate: 5 }}
          >
            <Shield className="w-5 h-5" style={{ color: primaryColor }} />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
          >
            <motion.p
              style={{
                color: primaryColor,
                fontWeight: 700,
                fontSize: 15,
                marginBottom: 4,
              }}
            >
              {verdictMessage}
            </motion.p>
            <motion.p
              style={{ fontSize: 12, color: '#6E6A62' }}
            >
              Protected by ABYSS Deception Engine
            </motion.p>
          </motion.div>
        </motion.div>

        <motion.button
          type="button"
          onClick={onDownload}
          style={{
            flexShrink: 0,
            padding: '12px 26px',
            background: 'linear-gradient(135deg, #FF2E55, #C0392B)',
            color: '#FFFFFF',
            fontSize: 12,
            fontFamily: "'JetBrains Mono', monospace",
            fontWeight: 800,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            border: 'none',
            borderRadius: 8,
            cursor: 'pointer',
            boxShadow: '0 0 25px rgba(255,46,85,0.4)',
          }}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.25 }}
          whileHover={{ y: -2, scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <motion.svg
            width="14"
            height="14"
            viewBox="0 0 14 14"
            fill="none"
            aria-hidden="true"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            style={{ marginRight: 6, display: 'inline-block', verticalAlign: 'middle', marginTop: -2 }}
          >
            <path
              d="M7 1v8M7 9l-3-3M7 9l3-3M2 12h10"
              stroke="white"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </motion.svg>
          Download Report
        </motion.button>
      </motion.div>
    </motion.div>
  );
}

// ─── Helper Components ─────────────────────────────────────────────────────────

function EmptyState({ text }: { text: string }) {
  return (
    <motion.p
      style={{
        fontSize: 12,
        color: 'rgba(0,0,0,0.4)',
        textAlign: 'center',
        padding: '16px 0',
        fontStyle: 'italic',
      }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.3 }}
    >
      {text}
    </motion.p>
  );
}

// ─── Style Constants ──────────────────────────────────────────────────────────

const listItemStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 8,
  padding: '10px 14px',
  borderRadius: 8,
  background: 'rgba(255, 255, 255, 0.03)',
  border: '1px solid rgba(255, 255, 255, 0.08)',
  minWidth: 0,
};

// ─── Utility Functions ────────────────────────────────────────────────────────

function getFileIcon(fileType: string | undefined): React.ReactNode {
  if (!fileType) return <FileText className="w-5 h-5 opacity-70" />;
  const t = fileType.toLowerCase();
  if (t.includes('exe') || t.includes('dll')) return <Cpu className="w-5 h-5 text-cyan-400" />;
  if (t.includes('pdf')) return <FileText className="w-5 h-5 text-red-400" />;
  if (t.includes('zip')) return <Archive className="w-5 h-5 text-indigo-400" />;
  if (t.includes('doc')) return <FileText className="w-5 h-5 text-blue-400" />;
  return <FileText className="w-5 h-5 opacity-70" />;
}

function getFileTypeIcon(type: StolenFile['type']): React.ReactNode {
  const map: Record<StolenFile['type'], React.ReactNode> = {
    document: <FileText className="w-4 h-4 text-slate-300" />,
    image: <FileText className="w-4 h-4 text-emerald-400" />,
    credential: <Key className="w-4 h-4 text-amber-400" />,
    database: <Database className="w-4 h-4 text-blue-400" />,
    config: <Settings className="w-4 h-4 text-slate-400" />,
  };
  return map[type] ?? <FileText className="w-4 h-4" />;
}

function getSeverityColor(severity: SeverityLevel): string {
  const map: Record<SeverityLevel, string> = {
    critical: '#EF4444',
    high: '#F97316',
    medium: '#F59E0B',
    low: '#3B82F6',
    info: '#64748B',
  };
  return map[severity] ?? '#3B82F6';
}

function getSeverityBadgeClass(severity: SeverityLevel): string {
  const map: Record<SeverityLevel, string> = {
    critical: 'badge-red',
    high: 'badge-red',
    medium: 'badge-amber',
    low: 'badge-blue',
    info: 'badge-cyan',
  };
  return map[severity] ?? 'badge-blue';
}

function getEventTypeIcon(type: TimelineEventType): React.ReactNode {
  const map: Record<TimelineEventType, React.ReactNode> = {
    file: <FileText className="w-3 h-3 text-blue-400" />,
    network: <Network className="w-3 h-3 text-cyan-400" />,
    registry: <Settings className="w-3 h-3 text-amber-400" />,
    process: <Cpu className="w-3 h-3 text-indigo-400" />,
    memory: <Database className="w-3 h-3 text-pink-400" />,
  };
  return map[type] ?? <FileText className="w-3 h-3" />;
}

function getRiskColor(score: number): string {
  if (score >= 80) return '#EF4444';
  if (score >= 60) return '#F97316';
  if (score >= 40) return '#F59E0B';
  return '#10B981';
}

function formatTimestamp(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return ts;
  }
}