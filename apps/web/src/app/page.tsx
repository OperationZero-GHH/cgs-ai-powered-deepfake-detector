import Link from "next/link";
import { Footer, Header, Mark } from "@/components/brand";

export default function HomePage() {
  return (
    <>
      <Header />
      <main id="main-content" className="home-page">
        <section className="home-hero">
          <div className="home-hero__grid" aria-hidden="true" />
          <div className="container home-hero__inner">
            <div className="home-hero__copy">
              <span className="eyebrow">Image evidence, with context</span>
              <h1>Inspect the image.<br /><span>Examine the evidence.</span></h1>
              <p>Review image integrity, technical metadata, and provenance clues without asking one detector to settle the truth.</p>
              <div className="hero-actions">
                <Link className="button button-primary" href="/sign-up">Start an inspection <span className="arrow" aria-hidden="true">→</span></Link>
                <Link className="button button-secondary" href="/solutions">Explore solutions</Link>
              </div>
              <div className="home-hero__assurance"><span aria-hidden="true">◈</span> Forensic indicators are evidence for review, never proof.</div>
            </div>

            <div className="hero-orbit" aria-label="Preview of an image inspection report">
              <div className="hero-orbit__halo" />
              <article className="float-card float-card--metadata">
                <div className="float-card__label"><span className="float-card__icon">01</span><span>FILE PROFILE</span></div>
                <strong>Image metadata</strong>
                <div className="float-card__data"><span>Format</span><b>JPEG</b></div>
                <div className="float-card__data"><span>Dimensions</span><b>2048 × 1365</b></div>
                <div className="float-card__data"><span>Integrity hash</span><b>Recorded</b></div>
              </article>

              <article className="float-card float-card--report">
                <div className="float-card__header"><div className="float-card__brand"><Mark small /><span>CGS / REPORT</span></div><span className="float-card__report-id">CASE 7F3A</span></div>
                <div className="float-card__image" aria-hidden="true"><span className="float-card__image-grid" /><span className="float-card__scan-line" /><span className="float-card__target float-card__target--a" /><span className="float-card__target float-card__target--b" /></div>
                <div className="float-card__result"><span className="float-card__status-dot" /><div><small>OVERALL RESULT</small><strong>Inconclusive</strong></div><span className="float-card__result-note">Review needed</span></div>
                <div className="float-card__report-foot"><span>Metadata observed</span><span>AI model unavailable</span></div>
              </article>

              <article className="float-card float-card--integrity">
                <span className="float-card__label"><span className="float-card__pulse" /> INTEGRITY CHECK</span>
                <strong>SHA-256</strong>
                <code>9f2c…a81e</code>
                <span className="float-card__verified">Hash recorded</span>
              </article>
              <div className="hero-orbit__caption"><span>01</span> A report built to show its limits</div>
            </div>
          </div>
          <div className="home-hero__bottom container"><span>JPEG · PNG · WEBP</span><span>BOUNDED DECODING</span><span>PRIVATE REPORT HISTORY</span><span>HUMAN REVIEW</span></div>
        </section>

        {/* Redesigned: Start with what can be checked */}
        <section className="public-section home-review-flow-v2" aria-labelledby="review-flow-title">
          <div className="container">
            <header className="section-header-v2">
              <span className="eyebrow-pill">
                <span className="eyebrow-dot" aria-hidden="true" />
                MULTI-LAYER FORENSIC PIPELINE
              </span>
              <h2 id="review-flow-title">Start with what can be checked.</h2>
              <p className="section-subtitle">
                A structured, four-phase inspection architecture that validates mathematical file structure,
                verifies provenance credentials, analyzes frequency-domain drift, and runs multi-model neural inference.
              </p>
            </header>

            <div className="pipeline-grid">
              <article className="pipeline-card">
                <div className="pipeline-card__header">
                  <span className="pipeline-badge">PHASE 01</span>
                  <span className="pipeline-type">STRUCTURAL AUDIT</span>
                </div>
                <h3>Cryptographic File Integrity</h3>
                <p>
                  Computes an immutable SHA-256 digest, enforces strict byte-allocation boundaries,
                  and inspects decoded image structures without relying on unverified headers.
                </p>
                <div className="pipeline-tags">
                  <span>SHA-256 Digest</span>
                  <span>Bounded Decoding</span>
                  <span>Format Sanity</span>
                </div>
              </article>

              <article className="pipeline-card">
                <div className="pipeline-card__header">
                  <span className="pipeline-badge">PHASE 02</span>
                  <span className="pipeline-type">PROVENANCE MANIFEST</span>
                </div>
                <h3>C2PA & Origin Provenance</h3>
                <p>
                  Disassembles embedded JUMBF metadata containers to verify hardware cryptographic signing keys,
                  camera attestation certificates, and editing histories.
                </p>
                <div className="pipeline-tags">
                  <span>C2PA v2.1 Manifest</span>
                  <span>Hardware Keys</span>
                  <span>Edit History</span>
                </div>
              </article>

              <article className="pipeline-card">
                <div className="pipeline-card__header">
                  <span className="pipeline-badge">PHASE 03</span>
                  <span className="pipeline-type">NEURAL ENSEMBLE</span>
                </div>
                <h3>Multi-Model Neural Screening</h3>
                <p>
                  Evaluates parallel Vision Transformers (ViT) and Wav2Vec2 models alongside
                  2D Fast Fourier Transform (FFT) spectral frequency drift analytics.
                </p>
                <div className="pipeline-tags">
                  <span>Dual ViT Ensembles</span>
                  <span>Wav2Vec2 Audio</span>
                  <span>2D-FFT Spectral Drift</span>
                </div>
              </article>

              <article className="pipeline-card">
                <div className="pipeline-card__header">
                  <span className="pipeline-badge">PHASE 04</span>
                  <span className="pipeline-type">CALIBRATED SYNTHESIS</span>
                </div>
                <h3>Calibrated Bounds & Disclosures</h3>
                <p>
                  Combines model outputs into calibrated probability distributions with agreement metrics,
                  conservatively defaulting to inconclusive whenever detectors diverge.
                </p>
                <div className="pipeline-tags">
                  <span>Bayesian Ensemble</span>
                  <span>Agreement Std-Dev</span>
                  <span>Visible Limits</span>
                </div>
              </article>
            </div>

            <div className="pipeline-footer-cta">
              <Link className="button button-primary btn-lime-themed" href="/sign-up">
                Start an inspection <span className="arrow" aria-hidden="true">→</span>
              </Link>
              <Link className="home-section-link-v2" href="/how-it-works">
                Explore technical methodology <span aria-hidden="true">→</span>
              </Link>
            </div>
          </div>
        </section>

        {/* Redesigned: A report describes signals. It doesn’t decide authenticity. */}
        <section className="public-section home-evidence-limits-v2" aria-labelledby="evidence-limits-title">
          <div className="container">
            <header className="section-header-v2 text-center">
              <span className="eyebrow-pill">
                <span className="eyebrow-dot" aria-hidden="true" />
                TRANSPARENCY & METHODOLOGY PRINCIPLES
              </span>
              <h2 id="evidence-limits-title">A report describes signals. It doesn’t decide authenticity.</h2>
              <p className="section-subtitle centered">
                Deepfake detection is not a binary switch. We provide reproducible empirical measurements with explicit boundaries,
                leaving consequential judgment to qualified human reviewers.
              </p>
            </header>

            <div className="evidence-matrix">
              {/* Left Column: What We Measure */}
              <div className="matrix-pane matrix-pane--verified">
                <div className="matrix-pane__head">
                  <span className="matrix-icon verified">✓</span>
                  <div>
                    <h3>What We Measure</h3>
                    <small>Empirical, reproducible forensic observations</small>
                  </div>
                </div>
                <div className="matrix-list">
                  <div className="matrix-item">
                    <strong>Cryptographic Envelope Fingerprint</strong>
                    <p>Exact SHA-256 payload digest matching against previous audits and tampering flags.</p>
                  </div>
                  <div className="matrix-item">
                    <strong>Frequency-Domain Fourier Drift</strong>
                    <p>Spectral power distribution variances produced by generative diffusion lattices and GAN upsamplers.</p>
                  </div>
                  <div className="matrix-item">
                    <strong>Multi-Model Ensemble Agreement</strong>
                    <p>Independent inference scores from distinct architectures with agreement variance metrics.</p>
                  </div>
                  <div className="matrix-item">
                    <strong>Hardware-Backed Origin Attestation</strong>
                    <p>Validated cryptographic certificate chains adhering strictly to C2PA provenance standards.</p>
                  </div>
                </div>
              </div>

              {/* Right Column: What We Reject */}
              <div className="matrix-pane matrix-pane--boundaries">
                <div className="matrix-pane__head">
                  <span className="matrix-icon boundaries">✕</span>
                  <div>
                    <h3>What We Reject</h3>
                    <small>Guarantees against overclaiming and false finality</small>
                  </div>
                </div>
                <div className="matrix-list">
                  <div className="matrix-item">
                    <strong>Zero Categorical "100% Real" Claims</strong>
                    <p>Absence of synthetic artifacts is never proof of reality. Real-world context is always required.</p>
                  </div>
                  <div className="matrix-item">
                    <strong>No Proprietary Black-Box Scoring</strong>
                    <p>Every individual model score, latency, and boundary condition is transparently reported.</p>
                  </div>
                  <div className="matrix-item">
                    <strong>No Silent Weight or API Drifts</strong>
                    <p>All neural models run locally and offline, strictly pinned to cryptographically locked commit hashes.</p>
                  </div>
                  <div className="matrix-item">
                    <strong>No Automated Human Replacements</strong>
                    <p>Our findings empower investigators; they never replace investigative expertise or legal deliberation.</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="matrix-callout">
              <div className="matrix-callout__pill">CORE COMMITMENT</div>
              <p>
                <strong>Inconclusive is a valid, responsible result:</strong> When detectors diverge, media is heavily compressed,
                or signals are ambiguous, CGS DeepFake Shield explicitly reports an inconclusive verdict rather than a misleading guess.
              </p>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
