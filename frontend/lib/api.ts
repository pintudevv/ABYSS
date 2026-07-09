/**
 * ABYSS API Client
 * Connects to backend at http://localhost:8000
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// ─── Types ────────────────────────────────────────────────────────────────────

export type ThreatType =
  | 'Trojan'
  | 'Ransomware'
  | 'Spyware'
  | 'Adware'
  | 'Rootkit'
  | 'Worm'
  | 'Backdoor'
  | 'Unknown'
  | 'Clean';

export type SeverityLevel = 'critical' | 'high' | 'medium' | 'low' | 'info';

export type TaskStatus =
  | 'pending'
  | 'extracting'
  | 'static_analysis'
  | 'sandbox'
  | 'ml_classification'
  | 'deception'
  | 'reporting'
  | 'complete'
  | 'failed';

export interface UploadResponse {
  task_id: string;
  filename: string;
  size: number;
  status: TaskStatus;
  message: string;
}

export interface StatusResponse {
  task_id: string;
  status: TaskStatus;
  progress: number; // 0-100
  current_stage: string;
  message: string;
  elapsed_seconds: number;
}

export interface StolenFile {
  path: string;
  type: 'document' | 'image' | 'credential' | 'database' | 'config';
  blocked: boolean;
}

export interface ExfilEndpoint {
  ip: string;
  domain: string;
  port: number;
  country: string;
  country_flag: string;
  protocol: string;
  sinkholed: boolean;
}

export interface MockData {
  original_type: string;
  mock_description: string;
  served_at: string;
}

export interface ApiHook {
  function_name: string;
  module: string;
  call_count: number;
  args_summary: string;
  severity: SeverityLevel;
}

export interface ShapFeature {
  name: string;
  impact: number;   // 0-1
  direction: 'positive' | 'negative';
  value: string;
}

export type TimelineEventType = 'file' | 'network' | 'registry' | 'process' | 'memory';

export interface TimelineEvent {
  timestamp: string;
  type: TimelineEventType;
  description: string;
  severity: SeverityLevel;
  details?: string;
}

export interface ThreatReport {
  task_id: string;
  filename: string;
  file_size: number;
  file_type: string;
  sha256: string;
  md5: string;
  analysis_duration_seconds: number;
  is_threat: boolean;
  threat_type: ThreatType;
  confidence: number; // 0-1
  is_zero_day: boolean;
  // Evidence
  stolen_files: StolenFile[];
  exfil_endpoints: ExfilEndpoint[];
  mock_data_served: MockData[];
  api_hooks: ApiHook[];
  // Intelligence
  shap_features: ShapFeature[];
  timeline: TimelineEvent[];
  // Summary
  risk_score: number; // 0-100
  risk_level?: string;
  verdict_message: string;
}

// ─── API Error ────────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// ─── Fetch Helper ─────────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${BASE_URL}${path}`;

  let response: Response;
  try {
    response = await fetch(url, {
      headers: {
        Accept: 'application/json',
        ...options?.headers,
      },
      ...options,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Network error';
    throw new ApiError(0, `Failed to reach ABYSS backend: ${message}`);
  }

  if (!response.ok) {
    let detail: string | undefined;
    try {
      const body = await response.json();
      detail = typeof body?.detail === 'string' ? body.detail : JSON.stringify(body);
    } catch {
      detail = await response.text();
    }
    throw new ApiError(response.status, `HTTP ${response.status}`, detail);
  }

  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError(0, 'Invalid JSON response from backend');
  }
}

// ─── API Functions ────────────────────────────────────────────────────────────

/**
 * Upload a file for malware analysis.
 * Returns the task_id to poll for status.
 */
export async function uploadFile(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append('file', file, file.name);

  return apiFetch<UploadResponse>('/analyze', {
    method: 'POST',
    body: form,
  });
}

/**
 * Poll the analysis status for a given task.
 */
export async function getStatus(taskId: string): Promise<StatusResponse> {
  if (!taskId || typeof taskId !== 'string') {
    throw new ApiError(400, 'Invalid task ID');
  }
  const sanitized = encodeURIComponent(taskId);
  return apiFetch<StatusResponse>(`/status/${sanitized}`);
}

export interface BackendReport {
  task_id: string;
  filename: string;
  file_hash_sha256: string;
  analysis_duration_seconds: number;
  threat_detected: boolean;
  threat_type: string;
  confidence: number;
  risk_level: string;
  is_zero_day: boolean;
  classifier_used: string;
  classification: {
    final_verdict: {
      label: string;
      confidence: number;
      threat_type: string;
      risk_level: string;
      reasoning: string;
    };
    ml_verdict: {
      threat_type: string;
      confidence: number;
      shap_explanation: Array<{
        feature: string;
        value: number;
        impact: number;
      }>;
      decision_path: string[];
    };
    dynamic_verdict: {
      dynamic_skipped?: boolean;
      skip_reason?: string;
      mock_mode: boolean;
      api_calls: Array<{
        timestamp: string;
        process: string;
        api: string;
        category: string;
        status: number;
        return_value: string;
        arguments: string[];
      }>;
      file_operations: Array<{
        path: string;
        operation: string;
        suspicious: boolean;
      }>;
      processes: Array<{
        name: string;
        pid: number;
        parent_pid: number;
        command_line: string;
      }>;
      network_connections?: Array<{
        dst_ip: string;
        dst_port: number;
        protocol: string;
        domain: string;
      }>;
      registry_operations: Array<{
        key: string;
        operation: string;
        blocked: boolean;
      }>;
      behavioral_indicators?: {
        trojan_apis?: string[];
        ransomware_apis?: string[];
        spyware_apis?: string[];
        network_apis?: string[];
      };
    };
  };
  static_features?: {
    file_info?: {
      file_size?: number;
      file_type?: string;
      md5?: string;
    };
    heuristic_risk?: {
      score?: number;
    };
  };
}

/**
 * Fetch the full threat report once analysis is complete.
 */
export async function getReport(taskId: string): Promise<ThreatReport> {
  if (!taskId || typeof taskId !== 'string') {
    throw new ApiError(400, 'Invalid task ID');
  }
  const sanitized = encodeURIComponent(taskId);
  const backendData = await apiFetch<BackendReport>(`/results/${sanitized}`);

  const shapExpl = backendData.classification?.ml_verdict?.shap_explanation || [];
  const maxAbsImpact = shapExpl.reduce((max, f) => Math.max(max, Math.abs(f.impact)), 0) || 1;

  const shap_features: ShapFeature[] = shapExpl.map(f => ({
    name: f.feature,
    impact: Math.abs(f.impact) / maxAbsImpact,
    direction: f.impact >= 0 ? 'positive' : 'negative',
    value: String(f.value),
  }));

  const apiCalls = backendData.classification?.dynamic_verdict?.api_calls || [];
  const trojanApis = backendData.classification?.dynamic_verdict?.behavioral_indicators?.trojan_apis || [];
  const api_hooks: ApiHook[] = apiCalls.map(c => ({
    function_name: c.api,
    module: "monitored",
    call_count: 1,
    args_summary: Array.isArray(c.arguments) && c.arguments.length > 0 ? String(c.arguments[0]) : "",
    severity: trojanApis.includes(c.api) ? "high" : "low",
  }));

  const fileOps = backendData.classification?.dynamic_verdict?.file_operations || [];
  const stolen_files: StolenFile[] = fileOps.map(f => ({
    path: f.path,
    type: "document",
    blocked: false,
  }));

  const netConns = backendData.classification?.dynamic_verdict?.network_connections || [];
  const exfil_endpoints: ExfilEndpoint[] = netConns.map(n => ({
    ip: n.dst_ip || "",
    domain: n.domain || "",
    port: n.dst_port || 80,
    country: "",
    country_flag: "🌐",
    protocol: n.protocol || "TCP",
    sinkholed: true,
  }));

  const decisionPath = backendData.classification?.ml_verdict?.decision_path || [];
  const timeline: TimelineEvent[] = decisionPath.map(item => ({
    timestamp: new Date().toISOString(),
    type: "process",
    description: item,
    severity: "medium",
    details: "",
  }));

  return {
    task_id: backendData.task_id || taskId,
    filename: backendData.filename,
    file_size: backendData.static_features?.file_info?.file_size || 0,
    file_type: backendData.static_features?.file_info?.file_type || "Unknown",
    sha256: backendData.file_hash_sha256 || "",
    md5: backendData.static_features?.file_info?.md5 || "",
    analysis_duration_seconds: backendData.analysis_duration_seconds || 0,
    is_threat: backendData.threat_detected,
    threat_type: backendData.threat_type as ThreatType,
    confidence: backendData.confidence / 100,
    is_zero_day: backendData.is_zero_day || false,
    stolen_files,
    exfil_endpoints,
    mock_data_served: [],
    api_hooks,
    shap_features,
    timeline,
    risk_score: backendData.static_features?.heuristic_risk?.score || backendData.confidence,
    risk_level: backendData.risk_level,
    verdict_message: backendData.classification?.final_verdict?.reasoning || "",
  };
}

/**
 * Download the forensic text report.
 * Returns a Blob URL for triggering download.
 */
export async function downloadReport(taskId: string): Promise<string> {
  if (!taskId || typeof taskId !== 'string') {
    throw new ApiError(400, 'Invalid task ID');
  }
  const sanitized = encodeURIComponent(taskId);
  const url = `${BASE_URL}/results/${sanitized}/download`;

  let response: Response;
  try {
    response = await fetch(url, { headers: { Accept: 'text/plain' } });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Network error';
    throw new ApiError(0, `Download failed: ${message}`);
  }

  if (!response.ok) {
    throw new ApiError(response.status, `Failed to download report`);
  }

  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

// ─── Utility ──────────────────────────────────────────────────────────────────

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(2)} ${units[i]}`;
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}m ${s}s`;
}

export const STAGE_LABELS: Record<TaskStatus, string> = {
  pending:          'Queued for analysis',
  extracting:       'Extracting PE features',
  static_analysis:  'Running static analysis',
  sandbox:          'Sandbox execution in progress',
  ml_classification:'ML classification',
  deception:        'Deception layer active',
  reporting:        'Generating forensic report',
  complete:         'Analysis complete',
  failed:           'Analysis failed',
};

export const STAGE_ORDER: TaskStatus[] = [
  'pending',
  'extracting',
  'static_analysis',
  'sandbox',
  'ml_classification',
  'deception',
  'reporting',
  'complete',
];
