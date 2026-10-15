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
        <section className="public-section home-review-flow" aria-labelledby="review-flow-title">
          <div className="container">
            <header className="section-header">
              <span className="eyebrow">A careful review, step by step</span>
              <h2 id="review-flow-title">Start with what can be checked.</h2>
            </header>
            <div className="workflow-rail">
              <article className="workflow-stage">
                <span className="workflow-number">01</span>
                <div className="workflow-stage__card">
                  <h3>Verify the file</h3>
                  <p>Check the image format, decoding boundaries, and integrity hash before interpreting its contents.</p>
                </div>
              </article>
              <article className="workflow-stage">
                <span className="workflow-number">02</span>
                <div className="workflow-stage__card">
                  <h3>Read its context</h3>
                  <p>Review available metadata and provenance clues alongside the image, not as a verdict on their own.</p>
                </div>
              </article>
              <article className="workflow-stage">
                <span className="workflow-number">03</span>
                <div className="workflow-stage__card">
                  <h3>Keep signals bounded</h3>
                  <p>See what automated checks can and cannot say, then leave consequential judgment to a person.</p>
                </div>
              </article>
            </div>
            <Link className="home-section-link" href="/how-it-works">See how review works <span aria-hidden="true">→</span></Link>
          </div>
        </section>
        <section className="public-section public-section--muted home-evidence-limits" aria-labelledby="evidence-limits-title">
          <div className="container home-evidence-limits__inner">
            <div className="section-header">
              <span className="eyebrow">Evidence, not a verdict</span>
              <h2 id="evidence-limits-title">A report describes signals. It doesn’t decide authenticity.</h2>
              <p>Every result stays attached to what was observed, what was available, and what still needs human context.</p>
            </div>
            <dl className="home-evidence-ledger">
              <div><dt>Verified</dt><dd>File integrity and supported image structure</dd></div>
              <div><dt>Observed</dt><dd>Metadata and provenance information present in the file</dd></div>
              <div><dt>Qualified</dt><dd>Automated signals, with method availability and limits made visible</dd></div>
            </dl>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
