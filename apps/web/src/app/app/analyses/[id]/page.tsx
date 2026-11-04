"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, formatBytes, formatDate, type Analysis } from "@/lib/api";
import { useAccountAccess } from "@/components/account-access-context";
import { NeuralScanOverlay } from "@/components/neural-scan-overlay";

function classificationLabel(value: string) {
  if (value === "likely_ai_generated" || value === "likely_manipulated") {
    return "Indicators Suggest Synthetic Manipulation";
  }
  if (value === "authentic_hardware_provenance") {
    return "Authentic Hardware Provenance (C2PA Verified)";
  }
  if (value === "likely_authentic") {
    return "Indicators Consistent with Natural Recording";
  }
  return "Inconclusive / Mixed Detector Signals";
}

function statusLabel(value: string) {
  return value.replaceAll("_", " ");
}

export default function AnalysisPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { status: accountAccess, refresh: refreshAccountAccess } = useAccountAccess();
  const [item, setItem] = useState<Analysis | null>(null);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [copiedHash, setCopiedHash] = useState(false);
  const [showNeuralOverlay, setShowNeuralOverlay] = useState(true);

  useEffect(() => {
    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function load() {
      try {
        const report = await api<Analysis>(`/analyses/${id}`);
        if (disposed) return;
        setItem(report);
        setError("");
        if (report.status === "failed") {
          window.dispatchEvent(new Event("cgs:account-refresh"));
          void refreshAccountAccess();
        }
        if (report.status === "queued" || report.status === "processing") {
          timer = setTimeout(load, 1500);
        }
      } catch (reason) {
        if (!disposed) setError(reason instanceof Error ? reason.message : "Unable to load report.");
      }
    }

    void load();
    return () => {
      disposed = true;
      if (timer) clearTimeout(timer);
    };
  }, [id, refreshAccountAccess]);

  async function remove() {
    if (!window.confirm("Permanently delete this forensic report and stored media? This cannot be undone.")) return;
    setDeleting(true);
    try {
      await api<void>(`/analyses/${id}`, { method: "DELETE" });
      router.replace(accountAccess?.is_authenticated ? "/app/history" : "/app/analyze");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to delete report.");
      setDeleting(false);
    }
  }

  function copyHash(hash: string) {
    void navigator.clipboard.writeText(hash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  }

  function downloadPdf() {
    const previousTitle = document.title;
    document.title = `CGS_Forensic_Report_${id.slice(0, 12)}`;
    window.print();
    window.setTimeout(() => { document.title = previousTitle; }, 1000);
  }

  if (error && !item) {
    return (
      <div className="dashboard-content">
        <div className="dash-hero-banner">
          <div>
            <span className="eyebrow text-danger">REPORT UNAVAILABLE</span>
            <h1>Could not load forensic record</h1>
            <p role="alert">{error}</p>
          </div>
          <Link className="button button-outline" href="/app/history">
            ← Back to history ledger
          </Link>
        </div>
      </div>
    );
  }

  if (!item) {
    return (
      <div className="dashboard-content">
        <div className="report-loading-box">
          <div className="auth-loading-spinner" aria-hidden="true" />
          <p>Decrypting and retrieving forensic report record…</p>
        </div>
      </div>
    );
  }

  const pending = item.status === "queued" || item.status === "processing";
  const failed = item.status === "failed";
  const synthetic = item.detectors.find(
    (d) =>
      d.task === "synthetic_image_detection" ||
      d.task === "video_deepfake_temporal_detection" ||
      d.task === "audio_deepfake_detection"
  );
  const isAiSignal =
    item.summary.classification === "likely_ai_generated" ||
    item.verdict === "likely_manipulated";
  const isVideo = Boolean(
    item.file.is_video ||
    item.media_type === "video" ||
    item.file.detected_mime_type?.startsWith("video/")
  );
  const isAudio = Boolean(
    item.file.is_audio ||
    item.media_type === "audio" ||
    item.file.detected_mime_type?.startsWith("audio/")
  );
  const models = item.models ?? [];
  const audioResult = item.audio;
  const spectral = synthetic?.spectral_forensics;
  const frameTimeline = synthetic?.frame_timeline;
  const layer1Spatial = synthetic?.layer1_spatial;
  const layer2Temporal = synthetic?.layer2_temporal;

  return (
    <div className="dashboard-content report-detail-page">
      {/* Top Heading Banner */}
      <div className="dash-hero-banner report-hero-banner no-print">
        <div className="dash-hero-info">
          <div className="dash-hero-eyebrow">
            <span className={`live-dot-pulse ${isAiSignal ? "pulse-amber" : ""}`} aria-hidden="true" />
            <span>
              FORENSIC EVIDENCE RECORD · {item.analysis_id.slice(0, 12).toUpperCase()}
            </span>
          </div>
          <h1>
            {isVideo
              ? "Video Deepfake Inspection Report"
              : isAudio
              ? "Audio Deepfake Inspection Report"
              : "Image Forensic Inspection Report"}
          </h1>
          <p>
            Generated on {formatDate(item.created_at)}
            {item.completed_at ? ` · Screening completed ${formatDate(item.completed_at)}` : ""}
          </p>
        </div>

        <div className="report-header-actions">
          <button
            className="button button-outline button-small"
            onClick={downloadPdf}
            disabled={pending}
            type="button"
          >
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <polyline points="6 9 6 2 18 2 18 9" />
              <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
              <rect x="6" y="14" width="12" height="8" />
            </svg>
            Download PDF
          </button>
          <button
            className="button button-outline-danger button-small"
            onClick={() => void remove()}
            disabled={deleting}
            type="button"
          >
            {deleting ? "Purging…" : "Purge Evidence"}
          </button>
        </div>
      </div>

      <header className="print-only report-print-header">
        <div className="report-print-brand">
          <img src="/cgs-logo.png" alt="" />
          <span>CGS<small>DEEPFAKE SHIELD</small></span>
        </div>
        <div className="report-print-meta">
          <strong>FORENSIC MEDIA REPORT</strong>
          <span>Report ID · {item.analysis_id.toUpperCase()}</span>
          <span>Inspection date · {formatDate(item.completed_at ?? item.created_at)}</span>
        </div>
      </header>

      {/* Overall Assessment Banner */}
      {(() => {
        const isHardwareAuth = item.summary.classification === "authentic_hardware_provenance";
        return (
          <div className={`report-verdict-banner ${pending || failed ? "is-pending" : isAiSignal ? "is-synthetic" : isHardwareAuth ? "is-hardware-trusted" : "is-authentic"}`}>
            <div className="verdict-banner-content">
              <span className="verdict-eyebrow">
                {failed ? "INSPECTION FAILED" : pending ? "INSPECTION STATUS" : isHardwareAuth ? "CRYPTOGRAPHIC PROVENANCE ATTESTATION" : "OVERALL SYNTHETIC MEDIA ASSESSMENT"}
              </span>
              <h2>
                {failed
                  ? "Analysis failed · please try again later"
                  : pending
                  ? item.status === "queued"
                    ? "Queued in persistent execution worker"
                    : "Neural forensic inference in progress…"
                  : classificationLabel(item.summary.classification)}
              </h2>
              <p>{item.summary.explanation}</p>
            </div>

            <div className="verdict-banner-pill">
              <span className={`verdict-pill-badge ${pending || failed ? "badge-pending" : isAiSignal ? "badge-caution" : isHardwareAuth ? "badge-hardware-trusted" : "badge-safe"}`}>
                {failed
                  ? "ANALYSIS FAILED"
                  : pending
                  ? statusLabel(item.status).toUpperCase()
                  : isAiSignal
                  ? "SYNTHETIC SIGNAL FLAGGED"
                  : isHardwareAuth
                  ? "C2PA HARDWARE AUTHENTICATED"
                  : "NO STRONG AI SIGNAL"}
              </span>
            </div>
          </div>
        );
      })()}

      {error && (
        <p role="alert" className="form-error">
          {error}
        </p>
      )}

      {/* Main Grid: Media & Detectors */}
      <div className="report-layout-grid">
        <div className="report-main-col">
          {/* Media Player / Viewer Card */}
          <section className="dash-panel report-media-card">
            <div className="panel-header">
              <div>
                <h3>
                  {isVideo
                    ? "Video Stream Inspection"
                    : isAudio
                    ? "Audio Stream Inspection"
                    : "Ingested Media Integrity"}
                </h3>
                <p>Private vault partition · Cryptographically fingerprinted</p>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", flexWrap: "wrap" }}>
                <button
                  type="button"
                  className={`neural-overlay-toggle ${showNeuralOverlay ? "is-active" : ""}`}
                  onClick={() => setShowNeuralOverlay((prev) => !prev)}
                  title="Toggle neural scanning lattice & telemetry reticle"
                >
                  <span aria-hidden="true">◈</span>
                  {showNeuralOverlay ? "Hide Neural Scan" : "Show Neural Scan"}
                </button>
                <span className="privacy-chip">
                  <i aria-hidden="true" /> {isVideo ? "VIDEO STREAM" : isAudio ? "AUDIO TRACK" : "STILL IMAGE"}
                </span>
              </div>
            </div>

            <div className="report-media-container" style={{ position: "relative" }}>
              {(pending || showNeuralOverlay) && (
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    zIndex: 10,
                    pointerEvents: pending ? "all" : "none",
                  }}
                >
                  <NeuralScanOverlay
                    mediaType={isVideo ? "video" : isAudio ? "audio" : "image"}
                    active={true}
                    isPending={pending}
                    statusText={
                      pending
                        ? "SCANNING ASSET TENSORS TO NEURAL MODEL"
                        : "NEURAL FORENSIC RETICLE & LATENT TENSORS"
                    }
                    fileName={item.file.original_filename}
                    dimensions={{ width: item.file.width, height: item.file.height }}
                  />
                </div>
              )}
              {isVideo ? (
                <>
                <div className="video-player-box no-print">
                  <video
                    controls
                    playsInline
                    className="report-video-element"
                    poster={item.file.image_url || undefined}
                    src={item.file.media_url || `/api/v1/analyses/${item.analysis_id}/original`}
                  >
                    Your browser does not support HTML5 video playback.
                  </video>
                </div>
                {item.file.image_url && <img className="print-only report-print-video-preview" src={item.file.image_url} alt="Representative video frame" />}
                </>
              ) : isAudio ? (
                <div className="audio-player-box" style={{ padding: "2.5rem 1.5rem", textAlign: "center" }}>
                  <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }} aria-hidden="true">🎵</div>
                  <audio
                    controls
                    className="report-audio-element"
                    src={item.file.media_url || `/api/v1/analyses/${item.analysis_id}/original`}
                    style={{ width: "100%", maxWidth: "480px" }}
                  >
                    Your browser does not support HTML5 audio playback.
                  </audio>
                </div>
              ) : (
                item.file.image_url && (
                  <div className="image-viewer-box">
                    <img
                      className="report-image-element"
                      src={item.file.image_url}
                      alt={`Normalized evidence preview of ${item.file.original_filename}`}
                    />
                  </div>
                )
              )}
            </div>

            {/* Technical Metadata Table */}
            <div className="report-tech-grid">
              <div className="tech-cell">
                <small>FILENAME</small>
                <strong>{item.file.original_filename}</strong>
              </div>
              <div className="tech-cell">
                <small>FORMAT &amp; SIZE</small>
                <strong>
                  {item.file.detected_mime_type} · {formatBytes(item.file.size_bytes)}
                </strong>
              </div>
              <div className="tech-cell">
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <small>TYPE VERIFICATION</small>
                  <span style={{ fontSize: "0.68rem", color: "#16a34a", fontWeight: 700 }}>VALIDATED</span>
                </div>
                <strong style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
                  <span style={{ color: "#84cc16" }}>✓</span>
                  Container Signature Matched
                </strong>
              </div>
              <div className="tech-cell">
                <small>DIMENSIONS</small>
                <strong>
                  {item.file.width} × {item.file.height} px
                </strong>
              </div>
              <div className="tech-cell hash-cell">
                <div className="hash-header">
                  <small>SHA-256 INTEGRITY DIGEST</small>
                  <button
                    type="button"
                    className="copy-hash-btn"
                    onClick={() => copyHash(item.file.sha256)}
                    title="Copy SHA-256 to clipboard"
                  >
                    {copiedHash ? "Copied!" : "Copy"}
                  </button>
                </div>
                <strong className="hash-string font-mono">{item.file.sha256}</strong>
              </div>
            </div>
          </section>

          {/* Video Temporal Continuity Forensics (if video) */}
          {isVideo && frameTimeline && frameTimeline.length > 0 && (
            <section className="dash-panel report-temporal-card">
              <div className="panel-header">
                <div>
                  <h3>Layer 1 · Spatial Keyframe Timeline</h3>
                  <p>Per-frame ONNX neural scoring across uniformly sampled keyframes</p>
                </div>
                <span className="setting-tag">{frameTimeline.length} FRAMES SAMPLED</span>
              </div>

              <div className="frame-timeline-list">
                {frameTimeline.map((f, i) => {
                  const score = f.layer1_score ?? f.score ?? 0;
                  const frameIsFake = score >= 0.65;
                  return (
                    <div key={i} className={`frame-timeline-item ${frameIsFake ? "frame-warning" : "frame-safe"}`}>
                      <div className="frame-index-col">
                        <span className="frame-number">FRAME #{i + 1}</span>
                        <span className="frame-time font-mono">@{f.timestamp_seconds}s</span>
                      </div>
                      <div className="frame-score-bar-wrap">
                        <div className="frame-score-label">
                          <span>Spatial Score: <strong>{(score * 100).toFixed(1)}%</strong></span>
                          <span className={`frame-tag ${frameIsFake ? "tag-fake" : "tag-real"}`}>
                            {frameIsFake ? "SYNTHETIC SIGNAL" : "NATURAL"}
                          </span>
                        </div>
                        <div className="frame-bar-track">
                          <div
                            className={`frame-bar-fill ${frameIsFake ? "bar-red" : "bar-green"}`}
                            style={{ width: `${Math.min(100, Math.max(5, score * 100))}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {layer1Spatial && (
                <div className="temporal-variance-footer">
                  <span>Mean Score: <strong className="font-mono">{(layer1Spatial.mean_score * 100).toFixed(1)}%</strong></span>
                  <span style={{ marginLeft: "1.5rem" }}>Peak Score: <strong className="font-mono">{(layer1Spatial.peak_score * 100).toFixed(1)}%</strong></span>
                  <span style={{ marginLeft: "1.5rem" }}>Variance: <strong className="font-mono">{layer1Spatial.variance}</strong></span>
                </div>
              )}
            </section>
          )}

          {/* Layer 2: Temporal LSTM Sequence Analysis */}
          {isVideo && layer2Temporal && layer2Temporal.status === "completed" && (
            <section className="dash-panel report-temporal-card">
              <div className="panel-header">
                <div>
                  <h3>Layer 2 · Temporal LSTM Sequence Analysis</h3>
                  <p>ResNext50 + LSTM cross-frame consistency reasoning</p>
                </div>
                <span className="setting-status-badge is-active">TEMPORAL LSTM</span>
              </div>

              <div className="detector-findings-box">
                <div className="detector-score-row">
                  <div className="detector-score-info">
                    <strong>
                      {layer2Temporal.label === "ai_generated_signal"
                        ? "Temporal Inconsistency Detected"
                        : "Temporal Consistency Verified"}
                    </strong>
                    <small>{layer2Temporal.model_id} · {layer2Temporal.model_version}</small>
                  </div>
                  <div className="score-badge-box">
                    <span className="score-val font-mono">
                      {layer2Temporal.score !== undefined
                        ? `${(layer2Temporal.score * 100).toFixed(1)}%`
                        : "—"}
                    </span>
                    <small>Ensemble Score</small>
                  </div>
                </div>

                <div className="spectral-metrics-grid" style={{ marginTop: "1rem" }}>
                  <div className="spectral-metric">
                    <small>LSTM TEMPORAL</small>
                    <strong className="font-mono">
                      {layer2Temporal.temporal_lstm_score !== undefined
                        ? `${(layer2Temporal.temporal_lstm_score * 100).toFixed(1)}%`
                        : "—"}
                    </strong>
                  </div>
                  <div className="spectral-metric">
                    <small>SPATIAL MEAN</small>
                    <strong className="font-mono">
                      {layer2Temporal.spatial_mean_score !== undefined
                        ? `${(layer2Temporal.spatial_mean_score * 100).toFixed(1)}%`
                        : "—"}
                    </strong>
                  </div>
                  <div className="spectral-metric">
                    <small>SPATIAL PEAK</small>
                    <strong className="font-mono">
                      {layer2Temporal.spatial_peak_score !== undefined
                        ? `${(layer2Temporal.spatial_peak_score * 100).toFixed(1)}%`
                        : "—"}
                    </strong>
                  </div>
                  <div className="spectral-metric">
                    <small>TEMPORAL DRIFT</small>
                    <strong className="font-mono">{layer2Temporal.temporal_drift ?? "—"}</strong>
                  </div>
                </div>

                {layer2Temporal.per_frame_scores && (
                  <div className="temporal-variance-footer" style={{ marginTop: "0.75rem" }}>
                    <span>Frames Processed: <strong>{layer2Temporal.frames_processed}</strong></span>
                    <span style={{ marginLeft: "1.5rem" }}>Temporal Variance: <strong className="font-mono">{layer2Temporal.temporal_variance}</strong></span>
                  </div>
                )}

                <p className="score-semantics-text" style={{ marginTop: "0.5rem" }}>{layer2Temporal.score_semantics}</p>
              </div>
            </section>
          )}

          {/* Multi-Model Ensemble Breakdown */}
          {models.length > 0 ? (
            <section className="dash-panel report-detector-card">
              <div className="panel-header">
                <div>
                  <h3>Multi-Model Neural Screening Ensemble</h3>
                  <p>Parallel evaluation across independent Vision Transformer and CNN architectures</p>
                </div>
                <span className="setting-status-badge is-active">
                  {item.confidence_band?.toUpperCase() ?? "MEDIUM"} CONFIDENCE
                </span>
              </div>

              <div className="detector-findings-box">
                <div className="detector-score-row">
                  <div className="detector-score-info">
                    <strong>
                      {isAiSignal
                        ? "Synthetic Generation Indicators Detected"
                        : item.verdict === "likely_authentic"
                        ? "Indicators Consistent with Natural Acquisition"
                        : "Ambiguous or Inconclusive Ensemble Signals"}
                    </strong>
                    <small>
                      Composite score: {(item.score !== undefined ? item.score * 100 : 50).toFixed(1)}% · Band: {item.confidence_band ?? "medium"}
                    </small>
                  </div>
                  <div className="score-badge-box">
                    <span className="score-val font-mono">
                      {(item.score !== undefined ? item.score * 100 : 50).toFixed(1)}%
                    </span>
                    <small>Composite Score</small>
                  </div>
                </div>

                <div className="score-progress-track">
                  <div
                    className={`score-progress-fill ${isAiSignal ? "fill-caution" : "fill-clean"}`}
                    style={{ width: `${Math.min(100, Math.max(5, (item.score ?? 0.5) * 100))}%` }}
                  />
                  <div className="threshold-marker" style={{ left: "65%" }} title="Threshold: 65%">
                    <span>Threshold: 65%</span>
                  </div>
                </div>

                <p className="score-semantics-text">{item.summary.explanation}</p>

                {/* Per-model breakdown list */}
                <div className="ensemble-models-list" style={{ marginTop: "1.25rem", borderTop: "1px solid var(--border)", paddingTop: "1rem" }}>
                  <h4 style={{ fontSize: "0.9rem", color: "var(--text-muted)", marginBottom: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    Contributing Model Classifiers
                  </h4>
                  <div style={{ display: "grid", gap: "0.75rem" }}>
                    {models.map((m, idx) => {
                      const isHigh = m.p_fake >= 0.65;
                      const modelFriendlyName =
                        m.name.includes("dima806")
                          ? "Dima ViT (Vision Transformer)"
                          : m.name.includes("prithivMLmods")
                          ? "Prithiv ViT-v2 (Deepfake Detector)"
                          : m.name.includes("Harshasnade")
                          ? "Harshasnade Hybrid (EfficientNetV2 + Swin)"
                          : m.name;
                      return (
                        <div
                          key={idx}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            padding: "0.6rem 0.85rem",
                            borderRadius: "6px",
                            background: "var(--surface-sunken, rgba(0,0,0,0.03))",
                            border: "1px solid var(--border)",
                            gap: "0.75rem",
                            flexWrap: "wrap",
                          }}
                        >
                          <div style={{ flex: 1, minWidth: "180px" }}>
                            <div style={{ fontWeight: 600, fontSize: "0.88rem" }}>
                              {modelFriendlyName}
                            </div>
                            <div style={{ fontSize: "0.76rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
                              commit {m.version.slice(0, 8)} {m.latency_ms ? `· ${m.latency_ms}ms` : ""}
                            </div>
                          </div>

                          <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                            {m.ok ? (
                              <>
                                <div style={{ textAlign: "right" }}>
                                  <div style={{ fontWeight: 700, fontSize: "0.95rem", color: isHigh ? "var(--danger, #f87171)" : "var(--accent, #06b6d4)" }}>
                                    {(m.p_fake * 100).toFixed(1)}%
                                  </div>
                                  {m.weight !== undefined && (
                                    <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
                                      Weight: {(m.weight * 100).toFixed(0)}%
                                    </div>
                                  )}
                                </div>
                                <span
                                  style={{
                                    fontSize: "0.72rem",
                                    padding: "0.2rem 0.5rem",
                                    borderRadius: "4px",
                                    fontWeight: 600,
                                    background: isHigh ? "rgba(239, 68, 68, 0.15)" : "rgba(34, 197, 94, 0.15)",
                                    color: isHigh ? "var(--danger, #f87171)" : "var(--success, #22c55e)",
                                  }}
                                >
                                  {isHigh ? "SYNTHETIC" : "NATURAL"}
                                </span>
                              </>
                            ) : (
                              <span
                                style={{
                                  fontSize: "0.75rem",
                                  padding: "0.2rem 0.5rem",
                                  borderRadius: "4px",
                                  background: "rgba(100, 116, 139, 0.15)",
                                  color: "var(--text-muted)",
                                }}
                              >
                                {m.error ?? "Offline / Disabled"}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Why this result accordion */}
                <details style={{ marginTop: "1rem", fontSize: "0.84rem", color: "var(--text-muted)" }}>
                  <summary style={{ cursor: "pointer", color: "var(--accent)", fontWeight: 600 }}>
                    Why this result? (Calibration &amp; Fallback Rules)
                  </summary>
                  <div style={{ padding: "0.75rem 0", lineHeight: 1.5 }}>
                    <p style={{ margin: "0 0 0.5rem" }}>
                      Each model&apos;s raw probability output undergoes Platt scaling calibration. 
                      The composite verdict requires consensus across independent models:
                    </p>
                    <ul style={{ paddingLeft: "1.2rem", margin: 0 }}>
                      <li><strong>Likely Manipulated:</strong> Weighted calibrated score ≥ 65% with inter-model standard deviation &lt; 0.35.</li>
                      <li><strong>Likely Authentic:</strong> Weighted calibrated score ≤ 35% with inter-model standard deviation &lt; 0.35.</li>
                      <li><strong>Inconclusive:</strong> Divergent model predictions, fewer than 2 active models, or scores falling in the ambiguity band (35%–65%).</li>
                    </ul>
                  </div>
                </details>
              </div>

              {/* Multi-Spectral Frequency Domain Analysis (FFT) */}
              {spectral && (
                <div className="spectral-analysis-block">
                  <h4>Multi-Spectral Frequency Domain Drift (FFT)</h4>
                  <div className="spectral-metrics-grid">
                    <div className="spectral-metric">
                      <small>HIGH-FREQ POWER</small>
                      <strong className="font-mono">{spectral.high_freq_power_db} dB</strong>
                    </div>
                    <div className="spectral-metric">
                      <small>LOW-FREQ POWER</small>
                      <strong className="font-mono">{spectral.low_freq_power_db} dB</strong>
                    </div>
                    <div className="spectral-metric">
                      <small>SPECTRAL DRIFT RATIO</small>
                      <strong className="font-mono text-accent">{spectral.spectral_drift_ratio}</strong>
                    </div>
                    <div className="spectral-metric">
                      <small>FOURIER DISPERSION</small>
                      <strong className="font-mono">{spectral.frequency_dispersion}</strong>
                    </div>
                  </div>
                </div>
              )}
            </section>
          ) : (
            <section className="dash-panel report-detector-card">
              <div className="panel-header">
                <div>
                  <h3>{isVideo ? "Dual-Layer Ensemble Verdict" : "Neural Artifact Screening"}</h3>
                  <p>{isVideo ? "Combined spatial ONNX + temporal LSTM ensemble calibration" : "FP16 ONNX DeepFake classifier & spatial upsampling detection"}</p>
                </div>
                <span className="setting-status-badge is-active">{isVideo && layer2Temporal ? "DUAL-LAYER" : "ONNX RUNTIME"}</span>
              </div>

              {!synthetic || synthetic.status === "queued" ? (
                <p className="system-note-body">Analysis queued for persistent background worker.</p>
              ) : synthetic.status === "completed" ? (
                <div className="detector-findings-box">
                  <div className="detector-score-row">
                    <div className="detector-score-info">
                      <strong>
                        {synthetic.label === "ai_generated_signal"
                          ? "Synthetic Generation Signal Detected"
                          : "No Strong AI Generation Signal"}
                      </strong>
                      <small>{synthetic.model_id} · {synthetic.model_version?.slice(0, 24)}</small>
                    </div>
                    <div className="score-badge-box">
                      <span className="score-val font-mono">
                        {synthetic.score === undefined || synthetic.score === null
                          ? "—"
                          : `${(synthetic.score * 100).toFixed(1)}%`}
                      </span>
                      <small>Screening Score</small>
                    </div>
                  </div>

                  <div className="score-progress-track">
                    <div
                      className={`score-progress-fill ${isAiSignal ? "fill-caution" : "fill-clean"}`}
                      style={{ width: `${Math.min(100, (synthetic.score ?? 0.1) * 100)}%` }}
                    />
                    <div className="threshold-marker" style={{ left: "65%" }} title="Threshold: 65%">
                      <span>Threshold: 65%</span>
                    </div>
                  </div>

                  <p className="score-semantics-text">{synthetic.score_semantics}</p>
                </div>
              ) : (
                <div className="detector-findings-box">
                  <p className="text-danger">AI screening unavailable: {synthetic.limitations?.[0] ?? "Inference error."}</p>
                </div>
              )}

              {/* Multi-Spectral Frequency Domain Analysis (FFT) */}
              {spectral && (
                <div className="spectral-analysis-block">
                  <h4>Multi-Spectral Frequency Domain Drift (FFT)</h4>
                  <div className="spectral-metrics-grid">
                    <div className="spectral-metric">
                      <small>HIGH-FREQ POWER</small>
                      <strong className="font-mono">{spectral.high_freq_power_db} dB</strong>
                    </div>
                    <div className="spectral-metric">
                      <small>LOW-FREQ POWER</small>
                      <strong className="font-mono">{spectral.low_freq_power_db} dB</strong>
                    </div>
                    <div className="spectral-metric">
                      <small>SPECTRAL DRIFT RATIO</small>
                      <strong className="font-mono text-accent">{spectral.spectral_drift_ratio}</strong>
                    </div>
                    <div className="spectral-metric">
                      <small>FOURIER DISPERSION</small>
                      <strong className="font-mono">{spectral.frequency_dispersion}</strong>
                    </div>
                  </div>
                </div>
              )}
            </section>
          )}

          {/* Audio Deepfake Forensics Card */}
          {(isAudio || (audioResult && audioResult.ok)) && (
            <section className="dash-panel report-detector-card">
              <div className="panel-header">
                <div>
                  <h3>Audio Deepfake &amp; Speech Anti-Spoofing Forensics</h3>
                  <p>Acoustic feature analysis and neural speech representation screening</p>
                </div>
                <span className="setting-status-badge is-active">WAV2VEC2</span>
              </div>

              <div className="detector-findings-box">
                {audioResult?.ok ? (
                  <>
                    <div className="detector-score-row">
                      <div className="detector-score-info">
                        <strong>
                          {audioResult.p_fake >= 0.65
                            ? "Synthetic Speech Artifacts Detected"
                            : audioResult.p_fake <= 0.35
                            ? "Acoustic Patterns Consistent with Natural Speech"
                            : "Inconclusive Speech Acoustic Patterns"}
                        </strong>
                        <small>
                          Vansh180/deepfake-audio-wav2vec2 · Analyzed {audioResult.duration_seconds.toFixed(1)}s
                        </small>
                      </div>
                      <div className="score-badge-box">
                        <span className="score-val font-mono">
                          {(audioResult.p_fake * 100).toFixed(1)}%
                        </span>
                        <small>Audio Score</small>
                      </div>
                    </div>

                    <div className="score-progress-track">
                      <div
                        className={`score-progress-fill ${audioResult.p_fake >= 0.65 ? "fill-caution" : "fill-clean"}`}
                        style={{ width: `${Math.min(100, Math.max(5, audioResult.p_fake * 100))}%` }}
                      />
                      <div className="threshold-marker" style={{ left: "65%" }} title="Threshold: 65%">
                        <span>Threshold: 65%</span>
                      </div>
                    </div>

                    <div className="spectral-metrics-grid" style={{ marginTop: "1rem" }}>
                      <div className="spectral-metric">
                        <small>ANALYZED DURATION</small>
                        <strong className="font-mono">{audioResult.duration_seconds.toFixed(1)}s</strong>
                      </div>
                      <div className="spectral-metric">
                        <small>WINDOWS ANALYZED</small>
                        <strong className="font-mono">{audioResult.windows_analyzed}</strong>
                      </div>
                      <div className="spectral-metric">
                        <small>WINDOWS FLAGGED</small>
                        <strong className="font-mono">{audioResult.windows_flagged}</strong>
                      </div>
                      <div className="spectral-metric">
                        <small>FLAG FRACTION</small>
                        <strong className="font-mono">{((audioResult.flag_fraction ?? 0) * 100).toFixed(1)}%</strong>
                      </div>
                    </div>

                    <p className="score-semantics-text" style={{ marginTop: "0.75rem" }}>
                      Audio deepfake detection screens for vocoder artifacts, acoustic boundaries, and phase inconsistencies.
                      Detection confidence can be affected by lossy audio compression and background acoustic noise.
                    </p>
                  </>
                ) : (
                  <p className="system-note-body" style={{ color: "var(--text-muted)" }}>
                    {audioResult?.error ?? (isAudio ? "Audio analysis was inconclusive or insufficient audio was detected." : "No audio track available for speech anti-spoofing.")}
                  </p>
                )}
              </div>
            </section>
          )}

          {/* Provenance & C2PA Ledger */}
          <section className="dash-panel report-provenance-card">
            <div className="panel-header">
              <div>
                <h3>Content Credentials &amp; Hardware Provenance</h3>
                <p>C2PA JUMBF cryptographic manifest and EXIF camera audit</p>
              </div>
              <span className="privacy-chip">
                <i aria-hidden="true" /> C2PA LEDGER
              </span>
            </div>

            <div className="provenance-details-list">
              <div className="provenance-item">
                <span>C2PA Manifest Status:</span>
                <strong>{statusLabel(item.provenance.status).toUpperCase()}</strong>
              </div>
              <div className="provenance-item">
                <span>EXIF Metadata Present:</span>
                <strong>{item.technical_integrity.exif_present ? "YES" : "NO"}</strong>
              </div>
              <div className="provenance-item">
                <span>ICC Color Profile:</span>
                <strong>{item.technical_integrity.icc_profile_present ? "EMBEDDED" : "NONE"}</strong>
              </div>
              {item.provenance.details?.map((line, i) => (
                <p key={i} className="provenance-subtext font-mono">{line}</p>
              ))}
            </div>
          </section>
        </div>

        {/* Right Sidebar: Guidance & Limitations */}
        <aside className="report-sidebar-col">
          <div className="dash-panel report-guide-card">
            <h4>How to Interpret This Report</h4>
            <p>
              The AI score indicates structural, spectral, and neural pattern alignment with known generative pipelines. It is a screening aid and should be evaluated alongside context.
            </p>
            <p>
              Natural images compressed repeatedly on social networks may occasionally experience frequency degradation. Content Credentials confirm unbroken provenance where hardware signatures exist.
            </p>
          </div>

          <div className="dash-panel report-warnings-card">
            <h4>Forensic Limitations &amp; Policy</h4>
            <ul>
              {item.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
            <p className="policy-note">
              This report is generated for evidence review and screening only. Do not use as the sole factor in high-impact legal, financial, or employment decisions.
            </p>
          </div>

          <div className="no-print">
            <Link href="/app/history" className="button button-outline button-wide">
              ← Return to Inspection Ledger
            </Link>
          </div>
        </aside>
      </div>
      <footer className="print-only report-print-footer">
        <strong>Interpretation and limitations.</strong> This report presents technical indicators for evidence review. Automated screening does not prove who created the media, whether it was edited, or whether depicted events are true. Consider original context and qualified human review before making consequential decisions.
        <br />Case {item.analysis_id.toUpperCase()} · SHA-256 {item.file.sha256}
      </footer>
    </div>
  );
}
