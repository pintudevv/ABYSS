/**
 * StealthOS API Client
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
    throw new ApiError(0, `Failed to reach StealthOS backend: ${message}`);
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

/**
 * Fetch the full threat report once analysis is complete.
 */
export async function getReport(taskId: string): Promise<ThreatReport> {
  if (!taskId || typeof taskId !== 'string') {
    throw new ApiError(400, 'Invalid task ID');
  }
  const sanitized = encodeURIComponent(taskId);
  return apiFetch<ThreatReport>(`/results/${sanitized}`);
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
