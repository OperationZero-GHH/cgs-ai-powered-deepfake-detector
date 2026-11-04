export type User = {
  id: string;
  email: string;
  display_name: string;
  username?: string | null;
  phone_number?: string | null;
  role: string;
  created_at: string;
  email_verified_at?: string | null;
};

export class ApiError extends Error {
  status: number;
  code?: string;
  referenceId?: string;
  contactEmail?: string | null;

  constructor(message: string, status: number, body: Record<string, unknown> | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = typeof body?.code === "string" ? body.code : undefined;
    this.referenceId = typeof body?.reference_id === "string" ? body.reference_id : undefined;
    this.contactEmail = typeof body?.contact_email === "string" ? body.contact_email : null;
  }
}

export type ModelBreakdown = {
  name: string;
  version: string;
  p_fake: number;
  calibrated_score?: number;
  weight?: number;
  ok: boolean;
  latency_ms?: number;
  error?: string | null;
  label_map_used?: Record<string, string>;
};

export type AudioBreakdown = {
  p_fake: number;
  duration_seconds: number;
  windows_analyzed: number;
  windows_flagged: number;
  flag_fraction: number;
  ok: boolean;
  error?: string | null;
  insufficient_audio?: boolean;
};

export type Analysis = {
  analysis_id: string;
  job_id?: string;
  media_type?: "image" | "video" | "audio";
  verdict?: "likely_authentic" | "inconclusive" | "likely_manipulated";
  confidence_band?: "low" | "medium" | "high";
  score?: number;
  models?: ModelBreakdown[];
  audio?: AudioBreakdown | null;
  frames_analyzed?: number;
  status: string;
  created_at: string;
  completed_at: string | null;
  file: {
    original_filename: string;
    detected_mime_type: string;
    size_bytes: number;
    width: number;
    height: number;
    sha256: string;
    image_url: string | null;
    media_url?: string | null;
    is_video?: boolean;
    is_audio?: boolean;
  };
  summary: {
    classification: string;
    confidence_kind: string;
    confidence_value: number | null;
    explanation: string;
  };
  detectors: Array<{
    task: string;
    status: string;
    provider?: string | null;
    model_id?: string | null;
    model_version?: string | null;
    label?: string | null;
    score?: number | null;
    score_semantics?: string | null;
    threshold?: number | null;
    threshold_policy_version?: string | null;
    latency_ms?: number | null;
    limitations?: string[];
    peak_score?: number | null;
    temporal_variance?: number | null;
    frames_analyzed?: number | null;
    total_duration_seconds?: number | null;
    frame_timeline?: Array<{
      frame_index: number;
      timestamp_seconds: number;
      score: number;
      layer1_score?: number;
      label: string;
    }>;
    layer1_spatial?: {
      mean_score: number;
      peak_score: number;
      variance: number;
      provider: string;
    };
    layer2_temporal?: {
      status: string;
      label?: string;
      model_id?: string;
      model_version?: string;
      score?: number;
      temporal_lstm_score?: number;
      spatial_mean_score?: number;
      spatial_peak_score?: number;
      temporal_drift?: number;
      frames_processed?: number;
      temporal_variance?: number;
      per_frame_scores?: number[];
      score_semantics?: string;
    };
    spectral_forensics?: {
      high_freq_power_db: number;
      low_freq_power_db: number;
      spectral_drift_ratio: number;
      frequency_dispersion: number;
    };
  }>;
  provenance: {
    status: string;
    validation_state?: string | null;
    assertion_labels?: string[];
    digital_source_types?: string[];
    details: string[];
  };
  technical_integrity: Record<string, string | number | boolean>;
  warnings: string[];
  report: { available: boolean; format: string };
};

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    credentials: "same-origin",
    cache: "no-store",
  });
  if (!response.ok) {
    const raw = await response.json().catch(() => null);
    const body = raw && typeof raw === "object" ? raw as Record<string, unknown> : null;
    const detail = body?.detail;
    const detailBody = detail && typeof detail === "object" ? detail as Record<string, unknown> : null;
    const message = typeof body?.message === "string"
      ? body.message
      : typeof detail === "string"
        ? detail
        : typeof detailBody?.message === "string"
          ? detailBody.message
      : response.status === 422
        ? "Some information needs attention. Check the form and try again."
        : `Request failed (${response.status}).`;
    throw new ApiError(message, response.status, body?.code ? body : detailBody ?? body);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function formatBytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(2)} MB`;
}
