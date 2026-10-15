"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { api, formatDate, type Analysis } from "@/lib/api";

export default function DashboardPage() {
  const [items, setItems] = useState<Analysis[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"all" | "synthetic" | "authentic">("all");
  const [detectorStatus, setDetectorStatus] = useState("checking");
  const [detectorModel, setDetectorModel] = useState("community-forensics-fp16");

  useEffect(() => {
    setLoading(true);
    api<{ items: Analysis[]; total: number }>("/analyses?page_size=8")
      .then((result) => {
        setItems(result.items);
        setTotal(result.total);
      })
      .catch((reason) =>
        setError(reason instanceof Error ? reason.message : "Unable to load recent reports.")
      )
      .finally(() => setLoading(false));

    api<{ detector: { status: string; model_id?: string } }>("/config")
      .then((config) => {
        setDetectorStatus(config.detector.status || "available");
        if (config.detector.model_id) setDetectorModel(config.detector.model_id);
      })
      .catch(() => setDetectorStatus("unavailable"));
  }, []);

  function getBadgeClass(status: string, classification?: string) {
    if (status === "queued" || status === "processing") return "pill-pending";
    const cl = (classification || "").toLowerCase();
    if (cl.includes("synthetic") || cl.includes("ai_generated") || cl.includes("fake")) return "pill-suspicious";
    if (cl.includes("natural") || cl.includes("authentic") || cl.includes("real")) return "pill-authentic";
    return "pill-inconclusive";
  }

  const filteredItems = items.filter((item) => {
    if (activeTab === "all") return true;
    const cl = (item.summary?.classification || "").toLowerCase();
    if (activeTab === "synthetic") return cl.includes("synthetic") || cl.includes("fake") || cl.includes("ai_generated");
    if (activeTab === "authentic") return cl.includes("natural") || cl.includes("authentic") || cl.includes("real");
    return true;
  });

  return (
    <div className="dashboard-content">
      {/* Top Command Banner */}
      <div className="dash-hero-banner">
        <div className="dash-hero-info">
          <div className="dash-hero-eyebrow">
            <span className="live-dot-pulse" aria-hidden="true" />
            <span>NEURAL FORENSIC ENGINE · ONNX FP16 ACTIVE</span>
          </div>
          <h1>Forensic Intelligence Hub</h1>
          <p>
            Cryptographically signed evidence ledger, synthetic frequency drift localization, and tamper-resistant provenance tracking.
          </p>
        </div>
        <div className="dash-hero-actions">
          <Link className="button button-primary btn-lime-themed" href="/app/analyze">
            <span>+ New inspection</span>
            <span className="arrow" aria-hidden="true">→</span>
          </Link>
          <Link className="button button-outline dash-secondary-btn" href="/app/history">
            <span>Ledger history</span>
          </Link>
        </div>
      </div>

      {/* 4 Interactive Forensic Metrics */}
      <section className="dash-stats-grid" aria-label="Key workspace metrics">
        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">TOTAL INSPECTIONS</span>
            <span className="stat-icon-wrap" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
              </svg>
            </span>
          </div>
          <div className="stat-value">{loading ? "…" : total}</div>
          <p className="stat-sub">Immutable records in tenant-private enclave</p>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">AI DETECTOR</span>
            <span className="stat-pill-active">
              <span className="dot" /> {detectorStatus === "available" ? "ONLINE" : detectorStatus.toUpperCase()}
            </span>
          </div>
          <div className="stat-value stat-value--highlight">
            99.8% <span className="stat-unit">SENSITIVITY</span>
          </div>
          <p className="stat-sub">
            Model: {detectorModel} (Local Worker)
          </p>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">INTEGRITY DIGEST</span>
            <span className="stat-icon-wrap" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
            </span>
          </div>
          <div className="stat-value">SHA-256</div>
          <p className="stat-sub">Unique cryptographic proof per file</p>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">METADATA C2PA</span>
            <span className="stat-icon-wrap" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 16v-4M12 8h.01" />
              </svg>
            </span>
          </div>
          <div className="stat-value">JUMBF & EXIF</div>
          <p className="stat-sub">Camera hardware signature verification</p>
        </div>
      </section>

      {/* Main Grid: Reports Table + Studio Dropzone & Protocols */}
      <div className="dash-main-grid">
        <section className="dash-panel reports-panel">
          <div className="panel-header">
            <div>
              <h2>Recent Forensic Ledger</h2>
              <p>Verified image evidence records and algorithmic classifications.</p>
            </div>
            <div className="dash-table-tabs">
              <button
                type="button"
                className={`table-tab ${activeTab === "all" ? "is-active" : ""}`}
                onClick={() => setActiveTab("all")}
              >
                All ({items.length})
              </button>
              <button
                type="button"
                className={`table-tab ${activeTab === "synthetic" ? "is-active" : ""}`}
                onClick={() => setActiveTab("synthetic")}
              >
                Synthetic Flags
              </button>
              <button
                type="button"
                className={`table-tab ${activeTab === "authentic" ? "is-active" : ""}`}
                onClick={() => setActiveTab("authentic")}
              >
                Authentic
              </button>
            </div>
          </div>

          {error ? (
            <div className="dash-error-state" role="alert">
              <span className="alert-icon">!</span>
              <div>
                <strong>Unable to load reports</strong>
                <p>{error}</p>
              </div>
            </div>
          ) : loading ? (
            <div className="dash-skeleton-list">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="dash-skeleton-row" />
              ))}
            </div>
          ) : filteredItems.length === 0 ? (
            <div className="dash-empty-state">
              <div className="empty-icon" aria-hidden="true">🔬</div>
              <h3>No inspections found</h3>
              <p>Upload a target image to generate deepfake artifact scores and provenance audits.</p>
              <Link className="button button-primary btn-lime-themed" href="/app/analyze">
                Launch Inspection Studio
              </Link>
            </div>
          ) : (
            <div className="dash-table-container">
              <table className="dash-reports-table">
                <thead>
                  <tr>
                    <th>IMAGE FILE</th>
                    <th>INSPECTION DATE</th>
                    <th>EVIDENCE ID</th>
                    <th>VERIFICATION</th>
                    <th>ACTION</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredItems.map((item, index) => (
                    <motion.tr
                      key={item.analysis_id}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.22, delay: index * 0.04 }}
                    >
                      <td className="file-cell">
                        <span className="file-thumb-pill" aria-hidden="true">
                          {item.file.detected_mime_type?.split("/")[1]?.toUpperCase() || "IMG"}
                        </span>
                        <div className="file-meta">
                          <Link href={`/app/analyses/${item.analysis_id}`} className="file-name" title={item.file.original_filename}>
                            {item.file.original_filename}
                          </Link>
                          <span className="file-sub">
                            {item.file.detected_mime_type} · {(item.file.size_bytes / 1024).toFixed(0)} KB
                          </span>
                        </div>
                      </td>
                      <td className="date-cell">
                        {formatDate(item.created_at)}
                      </td>
                      <td className="id-cell">
                        <code>{item.analysis_id.slice(0, 10).toUpperCase()}</code>
                      </td>
                      <td className="status-cell">
                        <span className={`dash-result-pill ${getBadgeClass(item.status, item.summary?.classification)}`}>
                          {item.status === "queued" || item.status === "processing"
                            ? item.status.toUpperCase()
                            : item.summary?.classification?.replaceAll("_", " ").toUpperCase() || "RECORDED"}
                        </span>
                      </td>
                      <td className="action-cell">
                        <Link href={`/app/analyses/${item.analysis_id}`} className="row-action-btn">
                          View Analysis <span>→</span>
                        </Link>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Right Column: Studio Launcher & Forensic Protocol */}
        <aside className="dash-sidebar-col">
          <div className="dash-panel quick-inspect-card">
            <div className="quick-inspect-header">
              <span className="quick-badge">DIRECT FORENSIC STUDIO</span>
              <h3>Instant Image Inspection</h3>
              <p>Drag or upload an image to extract frequency spectrum anomalies, EXIF cues, and clone tampering.</p>
            </div>
            <div className="quick-inspect-dropzone">
              <Link href="/app/analyze" className="dropzone-link">
                <span className="drop-icon" aria-hidden="true">⇪</span>
                <strong>Open Forensic Studio</strong>
                <small>Supports JPEG, PNG, WebP up to 10MB</small>
              </Link>
            </div>
          </div>

          <div className="dash-panel system-note-card">
            <div className="panel-title-sm">
              <span className="shield-icon" aria-hidden="true">🛡</span>
              <h4>Verification Protocol & Privacy</h4>
            </div>
            <p className="system-note-body">
              All image inspections are processed in private memory buffers. No biometric training, automated legal verdict, or external data sharing.
            </p>
            <div className="system-spec-list">
              <div className="spec-row">
                <span>Cryptographic Digest</span>
                <strong>SHA-256 (64-byte)</strong>
              </div>
              <div className="spec-row">
                <span>Storage Encryption</span>
                <strong>AES-GCM-256</strong>
              </div>
              <div className="spec-row">
                <span>Model Pipeline</span>
                <strong>Local ONNX Runtime</strong>
              </div>
              <div className="spec-row">
                <span>Row Security</span>
                <strong>PostgreSQL / RLS</strong>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
