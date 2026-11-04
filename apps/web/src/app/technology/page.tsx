import type { Metadata } from "next";
import Link from "next/link";
import { Footer, Header } from "@/components/brand";

export const metadata: Metadata = {
  title: "Technology & Forensic Architecture",
  description: "Independent multi-vector forensic architecture separating file container integrity, hardware provenance, frequency drift, neural ensemble inference, and temporal continuity.",
};

interface ForensicVector {
  number: string;
  badge: string;
  domain: string;
  title: string;
  targetQuestion: string;
  description: string;
  deliverable: string;
  bounds: string;
  tags: string[];
}

const forensicVectors: ForensicVector[] = [
  {
    number: "01",
    badge: "VECTOR 01",
    domain: "CONTAINER FORENSICS",
    title: "Cryptographic File Integrity & Memory-Safe Decoding",
    targetQuestion: "Has the digital byte stream been altered, corrupted, or crafted as an exploit payload?",
    description:
      "Every forensic inspection begins with a deterministic SHA-256 cryptographic digest to anchor the evidence chain of custody. Decoders operate under strict bounded memory buffers to neutralize decompression bombs (zip bombs / pixel flood vectors). The container layer verifies magic-byte signatures against declared MIME types and validates embedded ICC color profiles to prevent profile-stripping forgery.",
    deliverable: "Deterministic SHA-256 binary digest, format conformance log, buffer bounds audit, and color-space validity report.",
    bounds: "Integrity verification confirms whether bits have changed since hashing; it does not determine the real-world truth of depicted visual content.",
    tags: ["SHA-256 Digest", "Bounded Decompression", "ICC Profile Matrix", "Magic Byte Sanity"],
  },
  {
    number: "02",
    badge: "VECTOR 02",
    domain: "HARDWARE PROVENANCE",
    title: "C2PA Manifest Verification & Cryptographic Provenance",
    targetQuestion: "Does the media asset carry verifiable hardware certificates, camera signing keys, or authenticated edit history?",
    description:
      "Parses embedded JUMBF (JPEG Universal Metadata Box Format) containers according to ISO/IEC 19566-5 and C2PA v2.1 specifications. Extracts cryptographic signatures, validates hardware root-of-trust certificates issued to certified camera hardware, and verifies edit lineage manifests. The engine flags signature invalidation, missing certificate roots, or EXIF timestamp discrepancies.",
    deliverable: "C2PA manifest tree, hardware root-of-trust verification status, certified editing action chain, and EXIF consistency score.",
    bounds: "The absence of C2PA manifests is common on public platforms that strip metadata and is never treated as positive proof of manipulation.",
    tags: ["C2PA v2.1 Manifest", "JUMBF Box Tree", "Hardware Root-of-Trust", "EXIF Discrepancy"],
  },
  {
    number: "03",
    badge: "VECTOR 03",
    domain: "SPECTRAL ANALYSIS",
    title: "2D Fast Fourier Transform (FFT) & Error Level Analysis (ELA)",
    targetQuestion: "Are there high-frequency spatial periodicities or compression discontinuities from generative synthesis?",
    description:
      "Transforms spatial pixel grids into the 2D frequency spectrum using Fast Fourier Transform. Computes azimuthal power distributions to isolate the subtle periodic grid lattices left behind by convolutional deconvolution layers and latent diffusion upscalers. In tandem, Error Level Analysis (ELA) recalculates error differentials across quantization matrices to reveal spliced or composited regions.",
    deliverable: "Azimuthal frequency power curve, high-frequency lattice anomaly index, and ELA quantization variance map.",
    bounds: "Heavy lossy re-compression (e.g. repeated messaging app sharing) attenuates high-frequency data, yielding an explicit 'Inconclusive' flag rather than a false positive.",
    tags: ["2D FFT Residuals", "Azimuthal Power", "Error Level Analysis", "Quantization Heatmap"],
  },
  {
    number: "04",
    badge: "VECTOR 04",
    domain: "DEEP LEARNING",
    title: "Parallel Vision Transformer (ViT) Ensemble Inference",
    targetQuestion: "Do orthogonal deep feature extractors detect synthetic generative patterns?",
    description:
      "Employs parallel, fine-tuned Vision Transformer (ViT-Base/16) backbones trained on orthogonal synthetic datasets (including dima806 and prithivMLmods checkpoints). Instead of relying on a single model's bias, the engine evaluates cross-model agreement delta, patch-level attention distributions, and Platt-scaled calibrated probabilities. Models execute locally and completely offline with zero third-party API exposure.",
    deliverable: "Multi-model probability vector, architectural agreement delta, attention patch anomaly ranking, and calibrated ensemble score.",
    bounds: "Neural classifiers evaluate statistical similarity against training distributions; novel generative architectures may produce low anomaly scores until retrained.",
    tags: ["ViT-Base/16 Ensembles", "Platt Calibration", "Agreement Delta", "Offline PyTorch Runtime"],
  },
  {
    number: "05",
    badge: "VECTOR 05",
    domain: "TEMPORAL & ACOUSTIC",
    title: "Temporal Boundary Motion & Wav2Vec2 Acoustic Forensics",
    targetQuestion: "Does facial geometry warp over time, or does audio contain cloned voice vocoder signatures?",
    description:
      "For video sequences, samples keyframes and tracks temporal facial landmark continuity and optical flow coherence using the Harshasnade temporal network. For audio streams, audio is resampled to 16 kHz mono and evaluated through self-supervised Wav2Vec2 neural speech representations to detect vocoder phase anomalies, synthetic vocal tract formants, and splice boundaries.",
    deliverable: "Inter-frame facial jitter curve, optical flow variance score, Wav2Vec2 synthetic voice probability, and vocal spectrum spectrogram.",
    bounds: "Acoustic detection requires sufficient audio duration (minimum 1.5 seconds) and clean signal-to-noise ratio; heavy background noise triggers a low-confidence notice.",
    tags: ["Harshasnade Temporal Network", "Wav2Vec2 Acoustic Model", "Facial Landmark Jitter", "Vocoder Phase Forensics"],
  },
];

export default function TechnologyPage() {
  return (
    <>
      <Header />
      <main id="main-content" className="route-page tech-page">
        {/* Intro / Hero Section */}
        <section className="container tech-intro">
          <span className="eyebrow-pill">
            <span className="eyebrow-dot" aria-hidden="true" />
            MULTI-LAYER FORENSIC VERIFICATION ARCHITECTURE
          </span>
          <h1>Different questions need different evidence.</h1>
          <p className="section-subtitle">
            Forensic analysis cannot be reduced to a single black-box percentage score. CGS DeepFake Shield isolates
            container integrity, cryptographic provenance, frequency-domain drift, neural ensemble inference, and temporal
            continuity into five dedicated, accountable layers — each answering an explicit, bounded question with empirical proof.
          </p>

          <div className="tech-vector-pills" aria-label="Forensic evidence vectors">
            <span className="tech-vector-pill">01 · File & Memory Integrity</span>
            <span className="tech-vector-pill">02 · C2PA & Provenance Lineage</span>
            <span className="tech-vector-pill">03 · Spectral FFT & ELA Residuals</span>
            <span className="tech-vector-pill">04 · Vision Transformer Ensembles</span>
            <span className="tech-vector-pill">05 · Temporal Motion & Acoustic Forensics</span>
          </div>
        </section>

        {/* The 5 Dedicated Forensic Evidence Vectors */}
        <section className="container tech-vectors-container" aria-label="Evidence vector details">
          {forensicVectors.map((v) => (
            <article className="tech-vector-card" key={v.number}>
              <div className="tech-vector-card__main">
                <div className="tech-vector-card__header">
                  <span className="tech-vector-badge">{v.badge}</span>
                  <span className="tech-vector-domain">{v.domain}</span>
                </div>
                <h2>{v.title}</h2>

                <div className="tech-question-box">
                  <span>TARGET FORENSIC QUESTION</span>
                  <p>&ldquo;{v.targetQuestion}&rdquo;</p>
                </div>

                <p>{v.description}</p>

                <div className="tech-tag-row">
                  {v.tags.map((tag) => (
                    <span key={tag}>{tag}</span>
                  ))}
                </div>
              </div>

              <aside className="tech-vector-card__sidebar">
                <div className="tech-sidebar-block">
                  <h3>FORENSIC DELIVERABLE</h3>
                  <p>{v.deliverable}</p>
                </div>
                <div className="tech-sidebar-block bounds">
                  <h3>METHODOLOGICAL BOUNDS</h3>
                  <p>{v.bounds}</p>
                </div>
              </aside>
            </article>
          ))}
        </section>

        {/* Comparative Architecture: Segregated Evidence vs Monolithic Score */}
        <section className="container tech-compare-section" aria-labelledby="compare-heading">
          <header className="section-header-v2">
            <span className="eyebrow-pill">
              <span className="eyebrow-dot" aria-hidden="true" />
              ARCHITECTURAL DIFFERENTIATION
            </span>
            <h2 id="compare-heading">Segregated Forensic Layers vs The Monolithic Fallacy</h2>
            <p className="section-subtitle centered">
              Why collapsing multi-spectral observations into an opaque confidence percentage harms investigative credibility.
            </p>
          </header>

          <div className="evidence-matrix">
            {/* The Flawed Approach */}
            <div className="matrix-pane matrix-pane--boundaries">
              <div className="matrix-pane__head">
                <span className="matrix-icon boundaries">✕</span>
                <div>
                  <h3>Monolithic Black-Box Scores</h3>
                  <small>The industry trap: one opaque percentage</small>
                </div>
              </div>
              <div className="matrix-list">
                <div className="matrix-item">
                  <strong>Blends Incompatible Signals</strong>
                  <p>Mashes compression artifacts, metadata presence, and AI guesswork into an uninterpretable score like &ldquo;89% Fake&rdquo;.</p>
                </div>
                <div className="matrix-item">
                  <strong>False Alarms on Standard Compression</strong>
                  <p>Heavily re-saved images (WhatsApp, X, Instagram) trigger false positives because compression noise is misclassified as AI synthesis.</p>
                </div>
                <div className="matrix-item">
                  <strong>Legally &amp; Journalistically Indefensible</strong>
                  <p>Expert witnesses cannot explain what caused the score, rendering evidence inadmissible in courts or formal compliance audits.</p>
                </div>
                <div className="matrix-item">
                  <strong>Silent Failures on Novel Generative Models</strong>
                  <p>When an adversary uses an unobserved generation model, monolithic detectors fail catastrophically without raising a warning flag.</p>
                </div>
              </div>
            </div>

            {/* The CGS Approach */}
            <div className="matrix-pane matrix-pane--verified">
              <div className="matrix-pane__head">
                <span className="matrix-icon verified">✓</span>
                <div>
                  <h3>CGS Segregated Evidence Architecture</h3>
                  <small>The scientific standard: bounded, independent observations</small>
                </div>
              </div>
              <div className="matrix-list">
                <div className="matrix-item">
                  <strong>Independent Empirical Layers</strong>
                  <p>File structure, C2PA signatures, frequency residuals, and neural ensembles each report their own explicit observations and boundaries.</p>
                </div>
                <div className="matrix-item">
                  <strong>Honest &ldquo;Inconclusive&rdquo; Reporting</strong>
                  <p>When media is heavily degraded or detectors disagree, the platform explicitly flags the vector as inconclusive instead of guessing.</p>
                </div>
                <div className="matrix-item">
                  <strong>Full Chain of Custody &amp; Reproducibility</strong>
                  <p>SHA-256 fingerprint, model checkpoint hashes, and raw mathematical outputs provide an immutable audit trail for legal review.</p>
                </div>
                <div className="matrix-item">
                  <strong>Human-in-the-Loop Decision Support</strong>
                  <p>Empowers forensic analysts and investigators with actionable data while rejecting automated finality on consequential matters.</p>
                </div>
              </div>
            </div>
          </div>

          <div className="matrix-callout">
            <div className="matrix-callout__pill">CORE SCIENTIFIC PRINCIPLE</div>
            <p>
              <strong>A model score is an empirical observation of statistical correlation, never an absolute proof of truth:</strong> Absence of synthetic indicators is never definitive proof of authenticity. Real-world context and qualified human judgment remain indispensable.
            </p>
          </div>
        </section>

        {/* Technical Engine Specifications */}
        <section className="container tech-specs-card" aria-labelledby="specs-heading">
          <header className="section-header-v2">
            <span className="eyebrow-pill">
              <span className="eyebrow-dot" aria-hidden="true" />
              SYSTEM SPECIFICATIONS
            </span>
            <h2 id="specs-heading">Under the Hood: Engine Specifications</h2>
            <p className="section-subtitle">
              Verified technical configuration and runtime execution parameters powering CGS DeepFake Shield.
            </p>
          </header>

          <div className="tech-specs-grid">
            <div className="tech-spec-item">
              <span>VISION INFERENCE</span>
              <strong>ViT-Base/16 Dual Ensemble</strong>
              <small>Parallel dima806 &amp; prithivMLmods checkpoints running locally with PyTorch 2.5.</small>
            </div>
            <div className="tech-spec-item">
              <span>AUDIO FORENSICS</span>
              <strong>Wav2Vec2-XLSR-53</strong>
              <small>Self-supervised acoustic speech representation model resampled to 16 kHz mono.</small>
            </div>
            <div className="tech-spec-item">
              <span>TEMPORAL VIDEO</span>
              <strong>Harshasnade Motion Pipeline</strong>
              <small>Facial landmark consistency and optical flow displacement tracking across keyframes.</small>
            </div>
            <div className="tech-spec-item">
              <span>PROVENANCE PARSER</span>
              <strong>C2PA v2.1 &amp; ISO JUMBF</strong>
              <small>Hardware root-of-trust certificate validation and authenticated edit lineage verification.</small>
            </div>
            <div className="tech-spec-item">
              <span>FREQUENCY DOMAIN</span>
              <strong>2D FFT &amp; ELA Quantization</strong>
              <small>Azimuthal power integration and compression differential error level matrix analysis.</small>
            </div>
            <div className="tech-spec-item">
              <span>EXECUTION BOUNDARY</span>
              <strong>100% Offline Airgapped</strong>
              <small>Zero external API calls, zero telemetry leakage, and strict memory buffer protection.</small>
            </div>
          </div>
        </section>

        {/* Call to Action Banner */}
        <section className="container">
          <div className="tech-cta-box">
            <div className="tech-cta-box__copy">
              <h2>Examine digital evidence with scientific clarity.</h2>
              <p>
                Experience the multi-layer forensic inspection engine. Inspect image or media files with verifiable SHA-256 custody, C2PA provenance, and calibrated neural consensus.
              </p>
            </div>
            <div className="tech-cta-box__actions">
              <Link href="/scan" className="primary-button">
                Launch Forensic Scanner
              </Link>
              <Link href="/how-it-works" className="secondary-button">
                Review Full Methodology
              </Link>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
