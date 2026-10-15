"use client";

import { UploadForm } from "@/components/upload-form";

export default function AnalyzePage() {
  return (
    <div className="dashboard-content analyze-page-content">
      {/* Top Banner */}
      <div className="dash-hero-banner analyze-hero-banner">
        <div className="dash-hero-info">
          <div className="dash-hero-eyebrow">
            <span className="live-dot-pulse" aria-hidden="true" />
            <span>NEURAL STUDIO · MULTI-SPECTRAL IMAGE &amp; VIDEO FORENSICS</span>
          </div>
          <h1>Forensic Inspection Studio</h1>
          <p>
            Submit high-resolution images or videos for rigorous automated deepfake screening. The pipeline records cryptographic SHA-256 digests, inspects frequency-domain artifacts, evaluates video temporal continuity, and parses embedded provenance manifests.
          </p>
        </div>
        <div className="analyze-hero-specs">
          <div className="spec-badge">
            <span className="spec-badge-title">AI ENGINE</span>
            <strong>ONNX FP16</strong>
          </div>
          <div className="spec-badge">
            <span className="spec-badge-title">MODES</span>
            <strong>IMAGE &amp; VIDEO</strong>
          </div>
        </div>
      </div>

      <div className="analyze-studio-grid">
        {/* Left: Upload Studio Card */}
        <div className="dash-panel analyze-upload-panel">
          <div className="panel-header">
            <div>
              <h2>Media Ingestion &amp; Analysis</h2>
              <p>Drag and drop or select an image (JPEG, PNG, WebP) or video (MP4, WebM, MOV) for forensic evaluation.</p>
            </div>
            <span className="privacy-chip">
              <i aria-hidden="true" /> Ephemeral Buffer
            </span>
          </div>
          <UploadForm />
        </div>

        {/* Right: Studio Configuration & Protocol Card */}
        <aside className="analyze-sidebar-panel">
          <div className="dash-panel studio-config-card">
            <div className="panel-title-sm">
              <span className="shield-icon" aria-hidden="true">⚙</span>
              <h4>Configured Screening Pipeline</h4>
            </div>
            <p className="system-note-body">
              Active verification pipeline applied automatically during analysis:
            </p>

            <div className="screening-modules-list">
              <div className="screening-module-item">
                <span className="module-check" aria-hidden="true">✓</span>
                <div>
                  <strong>Spectral Frequency Drift (FFT/DCT)</strong>
                  <small>Detects GAN and diffusion upsampling patterns in mathematical frequency space</small>
                </div>
              </div>

              <div className="screening-module-item">
                <span className="module-check" aria-hidden="true">✓</span>
                <div>
                  <strong>Temporal Video Continuity</strong>
                  <small>Multi-frame video timeline extraction to detect localized face swaps &amp; flickering</small>
                </div>
              </div>

              <div className="screening-module-item">
                <span className="module-check" aria-hidden="true">✓</span>
                <div>
                  <strong>C2PA Provenance Ledger</strong>
                  <small>Extracts cryptographic hardware signatures and JUMBF manifests</small>
                </div>
              </div>

              <div className="screening-module-item">
                <span className="module-check" aria-hidden="true">✓</span>
                <div>
                  <strong>Pixel Seam Continuity</strong>
                  <small>Analyzes boundary blending, color temperature, and clone-stamp inconsistencies</small>
                </div>
              </div>

              <div className="screening-module-item">
                <span className="module-check" aria-hidden="true">✓</span>
                <div>
                  <strong>SHA-256 Digest Fingerprint</strong>
                  <small>Generates cryptographic proof of original file byte sequence</small>
                </div>
              </div>
            </div>
          </div>

          <div className="dash-panel studio-protocol-card">
            <div className="panel-title-sm">
              <span className="shield-icon" aria-hidden="true">🔒</span>
              <h4>Zero-Knowledge Data Protection</h4>
            </div>
            <p className="system-note-body">
              Uploaded image and video media is stored in tenant-isolated encrypted partitions. Content is never shared, indexed, or used for model retraining. You maintain complete retention control and can purge reports at any time.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
