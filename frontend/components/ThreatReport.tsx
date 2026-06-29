'use client';

import React from 'react';
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

interface ThreatReportProps {
  report: ThreatReport;
  onDownload: () => void;
}

export default function ThreatReportView({ report, onDownload }: ThreatReportProps) {
  const threatColor = report.is_threat ? '#ff3366' : '#00ff88';
  const confidencePct = Math.round(report.confidence * 100);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
      {/* ── Hero Header ────────────────────────────────────────────────────── */}
      <ReportHeader report={report} threatColor={threatColor} confidencePct={confidencePct} />

      {/* ── 4 Evidence Cards ───────────────────────────────────────────────── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: 20,
        }}
      >
        <StolenFilesCard files={report.stolen_files} />
        <ExfilCard endpoints={report.exfil_endpoints} />
        <MockDataCard mocks={report.mock_data_served} />
        <ApiHooksCard hooks={report.api_hooks} />
      </div>

      {/* ── SHAP Feature Importance ─────────────────────────────────────────── */}
      <ShapChart features={report.shap_features} />

      {/* ── Attack Timeline ─────────────────────────────────────────────────── */}
      <AttackTimeline events={report.timeline} />

      {/* ── Bottom Verdict ──────────────────────────────────────────────────── */}
      <VerdictFooter
        isThreat={report.is_threat}
        verdictMessage={report.verdict_message}
        onDownload={onDownload}
      />
    </div>
  );
}

// ─── Report Header ────────────────────────────────────────────────────────────

function ReportHeader({
  report,
  threatColor,
  confidencePct,
}: {
  report: ThreatReport;
  threatColor: string;
  confidencePct: number;
}) {
  return (
    <div
      className="glass-card animate-fade-in-up"
      style={{
        padding: '36px 32px',
        border: `1px solid ${threatColor}25`,
        boxShadow: `var(--shadow-card), 0 0 60px ${threatColor}08`,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 24,
          flexWrap: 'wrap',
        }}
      >
        {/* Left: file info + threat verdict */}
        <div style={{ flex: 1, minWidth: 260 }}>
          {/* Filename */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <span style={{ fontSize: 18, opacity: 0.7 }}>
              {getFileEmoji(report.file_type)}
            </span>
            <p
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 14,
                color: 'rgba(255,255,255,0.6)',
                wordBreak: 'break-all',
              }}
            >
              {report.filename}
            </p>
          </div>

          {/* Meta badges */}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 24 }}>
            <span className="glass-pill" style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)' }}>
              {formatFileSize(report.file_size)}
            </span>
            <span className="glass-pill" style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)' }}>
              {formatDuration(report.analysis_duration_seconds)}
            </span>
            <span className="glass-pill" style={{ fontSize: 11, fontFamily: "'JetBrains Mono', monospace", color: 'rgba(255,255,255,0.3)' }}>
              {report.sha256.slice(0, 16)}…
            </span>
          </div>

          {/* HUGE threat badge */}
          <div style={{ marginBottom: 16 }}>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 12,
                padding: '14px 24px',
                borderRadius: 14,
                background: report.is_threat
                  ? 'rgba(255,51,102,0.12)'
                  : 'rgba(0,255,136,0.10)',
                border: `1.5px solid ${threatColor}40`,
                animation: report.is_threat
                  ? 'pulse-glow-red 2s ease-in-out infinite'
                  : 'pulse-glow-green 2s ease-in-out infinite',
              }}
            >
              <span style={{ fontSize: 22 }}>{report.is_threat ? '⚠️' : '✅'}</span>
              <span
                style={{
                  fontSize: 22,
                  fontWeight: 800,
                  letterSpacing: '-0.01em',
                  color: threatColor,
                  textShadow: `0 0 24px ${threatColor}80`,
                }}
              >
                {report.is_threat ? 'THREAT DETECTED' : 'FILE CLEAN'}
              </span>
            </div>
          </div>

          {/* Threat type + zero-day */}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            {report.is_threat && (
              <span
                className="badge"
                style={{
                  background: 'rgba(255,51,102,0.18)',
                  color: '#ff6688',
                  border: '1px solid rgba(255,51,102,0.35)',
                  fontSize: 12,
                  padding: '5px 14px',
                }}
              >
                {report.threat_type}
              </span>
            )}
            {report.is_zero_day && (
              <span
                className="badge"
                style={{
                  background: 'rgba(255,170,0,0.15)',
                  color: '#ffaa00',
                  border: '1px solid rgba(255,170,0,0.3)',
                  fontSize: 12,
                  padding: '5px 14px',
                  animation: 'pulse-glow-blue 2.5s ease-in-out infinite',
                }}
              >
                ⚡ ZERO-DAY
              </span>
            )}
            <span
              style={{
                fontSize: 12,
                color: 'rgba(255,255,255,0.35)',
                padding: '4px 0',
              }}
            >
              Risk Score:{' '}
              <span style={{ color: getRiskColor(report.risk_score), fontWeight: 700 }}>
                {report.risk_score}/100
              </span>
            </span>
          </div>
        </div>

        {/* Right: Circular confidence meter */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <CircularProgress
            value={confidencePct}
            size={140}
            strokeWidth={8}
            color={threatColor}
            label="Confidence"
            sublabel="ML Score"
          />
          <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', textAlign: 'center' }}>
            Hybrid ML Ensemble
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── Stolen Files Card ────────────────────────────────────────────────────────

function StolenFilesCard({ files }: { files: StolenFile[] }) {
  return (
    <EvidenceCard
      title="Data It Tried to Steal"
      icon="📂"
      accentColor="#ff3366"
      animationClass="animate-fade-in-up stagger-1"
      count={files.length}
    >
      {files.length === 0 ? (
        <EmptyState text="No file access attempts recorded" />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {files.map((f, i) => (
            <div key={i} style={listItemStyle}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                <span style={{ fontSize: 13, opacity: 0.7 }}>{getFileTypeEmoji(f.type)}</span>
                <span
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 11,
                    color: 'rgba(255,255,255,0.65)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {f.path}
                </span>
              </div>
              {f.blocked && <span className="badge badge-red">BLOCKED</span>}
            </div>
          ))}
        </div>
      )}
    </EvidenceCard>
  );
}

// ─── Exfil Endpoints Card ─────────────────────────────────────────────────────

function ExfilCard({ endpoints }: { endpoints: ExfilEndpoint[] }) {
  return (
    <EvidenceCard
      title="Where It Tried to Send It"
      icon="🌐"
      accentColor="#ff3366"
      animationClass="animate-fade-in-up stagger-2"
      count={endpoints.length}
    >
      {endpoints.length === 0 ? (
        <EmptyState text="No exfiltration attempts detected" />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {endpoints.map((ep, i) => (
            <div key={i} style={listItemStyle}>
              <div style={{ minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontSize: 13 }}>{ep.country_flag}</span>
                  <span
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 11,
                      color: '#ff8899',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {ep.domain || ep.ip}:{ep.port}
                  </span>
                </div>
                <p style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', marginTop: 1 }}>
                  {ep.protocol} · {ep.country}
                </p>
              </div>
              {ep.sinkholed && <span className="badge badge-amber">SINKHOLED</span>}
            </div>
          ))}
        </div>
      )}
    </EvidenceCard>
  );
}

// ─── Mock Data Card ───────────────────────────────────────────────────────────

function MockDataCard({ mocks }: { mocks: MockData[] }) {
  return (
    <EvidenceCard
      title="What We Gave It Instead"
      icon="🎭"
      accentColor="#6366f1"
      animationClass="animate-fade-in-up stagger-3"
      count={mocks.length}
    >
      {mocks.length === 0 ? (
        <EmptyState text="No mock data required" />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {mocks.map((m, i) => (
            <div key={i} style={listItemStyle}>
              <div style={{ minWidth: 0 }}>
                <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)', marginBottom: 2 }}>
                  {m.mock_description}
                </p>
                <p
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 10,
                    color: 'rgba(255,255,255,0.3)',
                  }}
                >
                  Served at: {m.served_at}
                </p>
              </div>
              <span className="badge badge-blue">MOCK</span>
            </div>
          ))}
        </div>
      )}
    </EvidenceCard>
  );
}

// ─── API Hooks Card ───────────────────────────────────────────────────────────

function ApiHooksCard({ hooks }: { hooks: ApiHook[] }) {
  return (
    <EvidenceCard
      title="API Hooks Triggered"
      icon="🔗"
      accentColor="#22d3ee"
      animationClass="animate-fade-in-up stagger-4"
      count={hooks.length}
    >
      {hooks.length === 0 ? (
        <EmptyState text="No suspicious API calls detected" />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {hooks.map((h, i) => (
            <div key={i} style={listItemStyle}>
              <div style={{ minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span
                    className={`badge ${getSeverityBadgeClass(h.severity)}`}
                    style={{ fontSize: 9, padding: '2px 7px' }}
                  >
                    {h.severity.toUpperCase()}
                  </span>
                  <span
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 11,
                      color: '#22d3ee',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {h.function_name}
                  </span>
                </div>
                <p style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', marginTop: 2 }}>
                  {h.module} · Called ×{h.call_count}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </EvidenceCard>
  );
}

// ─── Evidence Card Wrapper ────────────────────────────────────────────────────

function EvidenceCard({
  title,
  icon,
  accentColor,
  animationClass,
  count,
  children,
}: {
  title: string;
  icon: string;
  accentColor: string;
  animationClass: string;
  count: number;
  children: React.ReactNode;
}) {
  return (
    <div
      className={`glass-card ${animationClass}`}
      style={{ padding: '22px 20px' }}
    >
      {/* Card header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 16,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 16 }}>{icon}</span>
          <h3
            style={{
              fontSize: 12,
              fontWeight: 700,
              letterSpacing: '0.07em',
              textTransform: 'uppercase',
              color: 'rgba(255,255,255,0.55)',
            }}
          >
            {title}
          </h3>
        </div>
        <span
          style={{
            fontSize: 13,
            fontWeight: 700,
            color: count > 0 ? accentColor : 'rgba(255,255,255,0.25)',
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          {count}
        </span>
      </div>

      {/* Divider */}
      <div
        style={{
          height: 1,
          background: `linear-gradient(90deg, ${accentColor}30 0%, transparent 100%)`,
          marginBottom: 14,
        }}
      />

      {children}
    </div>
  );
}

// ─── SHAP Feature Chart ───────────────────────────────────────────────────────

function ShapChart({ features }: { features: ShapFeature[] }) {
  if (features.length === 0) return null;

  const maxImpact = Math.max(...features.map((f) => Math.abs(f.impact)));
  const sorted = [...features].sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact)).slice(0, 10);

  return (
    <div
      className="glass-card animate-fade-in-up stagger-5"
      style={{ padding: '28px 24px' }}
    >
      <div style={{ marginBottom: 20 }}>
        <h3
          style={{
            fontSize: 12,
            fontWeight: 700,
            letterSpacing: '0.07em',
            textTransform: 'uppercase',
            color: 'rgba(255,255,255,0.55)',
            marginBottom: 4,
          }}
        >
          SHAP Feature Importance
        </h3>
        <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.3)' }}>
          Top features influencing the ML classification decision
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {sorted.map((feature, i) => {
          const pct = (Math.abs(feature.impact) / maxImpact) * 100;
          const color = feature.direction === 'positive' ? '#ff3366' : '#6366f1';
          return (
            <div key={i} className={`stagger-${i + 1}`} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              {/* Feature name */}
              <div style={{ width: 200, flexShrink: 0 }}>
                <p
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 11,
                    color: 'rgba(255,255,255,0.65)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                  title={feature.name}
                >
                  {feature.name}
                </p>
                <p style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', marginTop: 1 }}>
                  val: {feature.value}
                </p>
              </div>

              {/* Bar */}
              <div style={{ flex: 1, position: 'relative', height: 24 }}>
                <div
                  style={{
                    position: 'absolute',
                    inset: 0,
                    borderRadius: 4,
                    background: 'rgba(255,255,255,0.04)',
                  }}
                />
                <div
                  className="shap-bar"
                  style={{
                    position: 'absolute',
                    left: 0,
                    top: 0,
                    bottom: 0,
                    width: `${pct}%`,
                    borderRadius: 4,
                    background: `linear-gradient(90deg, ${color}cc, ${color}55)`,
                    animationDelay: `${i * 0.08}s`,
                    boxShadow: `0 0 12px ${color}30`,
                  }}
                />
                <div
                  style={{
                    position: 'absolute',
                    right: 8,
                    top: 0,
                    bottom: 0,
                    display: 'flex',
                    alignItems: 'center',
                  }}
                >
                  <span
                    style={{
                      fontSize: 10,
                      fontFamily: "'JetBrains Mono', monospace",
                      color: 'rgba(255,255,255,0.4)',
                    }}
                  >
                    {feature.impact.toFixed(3)}
                  </span>
                </div>
              </div>

              {/* Direction badge */}
              <span
                className={`badge ${feature.direction === 'positive' ? 'badge-red' : 'badge-blue'}`}
                style={{ fontSize: 9, padding: '2px 8px', flexShrink: 0 }}
              >
                {feature.direction === 'positive' ? '▲ MAL' : '▼ BEN'}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Attack Timeline ──────────────────────────────────────────────────────────

function AttackTimeline({ events }: { events: TimelineEvent[] }) {
  if (events.length === 0) return null;

  const sorted = [...events].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  );

  return (
    <div
      className="glass-card animate-fade-in-up stagger-6"
      style={{ padding: '28px 24px' }}
    >
      <div style={{ marginBottom: 24 }}>
        <h3
          style={{
            fontSize: 12,
            fontWeight: 700,
            letterSpacing: '0.07em',
            textTransform: 'uppercase',
            color: 'rgba(255,255,255,0.55)',
            marginBottom: 4,
          }}
        >
          Attack Timeline
        </h3>
        <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.3)' }}>
          {sorted.length} events recorded during sandbox execution
        </p>
      </div>

      <div style={{ position: 'relative', paddingLeft: 40 }}>
        {/* Vertical line */}
        <div className="timeline-line" />

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {sorted.map((event, i) => (
            <TimelineItem key={i} event={event} index={i} isLast={i === sorted.length - 1} />
          ))}
        </div>
      </div>
    </div>
  );
}

function TimelineItem({
  event,
  index,
  isLast,
}: {
  event: TimelineEvent;
  index: number;
  isLast: boolean;
}) {
  const color = getSeverityColor(event.severity);

  return (
    <div
      className={`animate-slide-in-left stagger-${Math.min(index + 1, 10)}`}
      style={{ display: 'flex', alignItems: 'flex-start', gap: 12, position: 'relative' }}
    >
      {/* Dot */}
      <div
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
          boxShadow: `0 0 10px ${color}25`,
        }}
      >
        {getEventTypeIcon(event.type)}
      </div>

      {/* Content */}
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
          <p style={{ fontSize: 13, color: 'rgba(255,255,255,0.8)', lineHeight: 1.4, flex: 1 }}>
            {event.description}
          </p>
          <span
            className={`badge ${getSeverityBadgeClass(event.severity)}`}
            style={{ fontSize: 9, padding: '2px 8px', flexShrink: 0 }}
          >
            {event.severity.toUpperCase()}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 4 }}>
          <span
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10,
              color: 'rgba(255,255,255,0.3)',
            }}
          >
            {formatTimestamp(event.timestamp)}
          </span>
          <span
            style={{
              fontSize: 10,
              color: color,
              textTransform: 'capitalize',
            }}
          >
            {event.type}
          </span>
        </div>
        {event.details && (
          <p
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10,
              color: 'rgba(255,255,255,0.25)',
              marginTop: 4,
              background: 'rgba(255,255,255,0.03)',
              padding: '4px 8px',
              borderRadius: 6,
            }}
          >
            {event.details}
          </p>
        )}
      </div>
    </div>
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
  return (
    <div
      className="glass-card animate-fade-in-up stagger-7"
      style={{
        padding: '28px 24px',
        border: `1px solid ${isThreat ? 'rgba(0,255,136,0.2)' : 'rgba(0,255,136,0.2)'}`,
        background: isThreat
          ? 'rgba(0,255,136,0.04)'
          : 'rgba(0,255,136,0.04)',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 20,
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              background: 'rgba(0,255,136,0.12)',
              border: '1px solid rgba(0,255,136,0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 20,
              flexShrink: 0,
            }}
          >
            🛡️
          </div>
          <div>
            <p
              style={{
                color: '#00ff88',
                fontWeight: 600,
                fontSize: 15,
                marginBottom: 4,
                textShadow: '0 0 16px rgba(0,255,136,0.4)',
              }}
            >
              {verdictMessage}
            </p>
            <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>
              Protected by StealthOS Deception Engine
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={onDownload}
          className="btn-primary"
          style={{ flexShrink: 0 }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
            <path d="M7 1v8M7 9l-3-3M7 9l3-3M2 12h10" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Download Report
        </button>
      </div>
    </div>
  );
}

// ─── Helper Components ────────────────────────────────────────────────────────

function EmptyState({ text }: { text: string }) {
  return (
    <p
      style={{
        fontSize: 12,
        color: 'rgba(255,255,255,0.25)',
        textAlign: 'center',
        padding: '16px 0',
        fontStyle: 'italic',
      }}
    >
      {text}
    </p>
  );
}

// ─── Style Constants ──────────────────────────────────────────────────────────

const listItemStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 8,
  padding: '8px 10px',
  borderRadius: 8,
  background: 'rgba(255,255,255,0.03)',
  border: '1px solid rgba(255,255,255,0.05)',
  minWidth: 0,
};

// ─── Utility Functions ────────────────────────────────────────────────────────

function getFileEmoji(fileType: string): string {
  const t = fileType.toLowerCase();
  if (t.includes('exe') || t.includes('dll')) return '⚙️';
  if (t.includes('pdf')) return '📄';
  if (t.includes('zip')) return '📦';
  if (t.includes('doc')) return '📝';
  return '📁';
}

function getFileTypeEmoji(type: StolenFile['type']): string {
  const map: Record<StolenFile['type'], string> = {
    document: '📄',
    image: '🖼️',
    credential: '🔑',
    database: '🗄️',
    config: '⚙️',
  };
  return map[type] ?? '📁';
}

function getSeverityColor(severity: SeverityLevel): string {
  const map: Record<SeverityLevel, string> = {
    critical: '#ff3366',
    high: '#ff6644',
    medium: '#ffaa00',
    low: '#6366f1',
    info: '#22d3ee',
  };
  return map[severity] ?? '#6366f1';
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

function getEventTypeIcon(type: TimelineEventType): string {
  const map: Record<TimelineEventType, string> = {
    file: '📄',
    network: '🌐',
    registry: '🔧',
    process: '⚡',
    memory: '💾',
  };
  return map[type] ?? '·';
}

function getRiskColor(score: number): string {
  if (score >= 80) return '#ff3366';
  if (score >= 60) return '#ff6644';
  if (score >= 40) return '#ffaa00';
  return '#00ff88';
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
