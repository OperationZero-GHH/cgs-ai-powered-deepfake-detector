import type { Metadata } from "next";
import { Footer, Header } from "@/components/brand";
import { ContactForm } from "@/components/contact-form";

export const metadata: Metadata = { title: "Contact & Security Desk" };

export default function ContactPage() {
  return (
    <>
      <Header />
      <main id="main-content" className="route-page contact-page">
        <section className="container contact-hero">
          <div className="contact-hero__copy">
            <span className="eyebrow">Direct Communications & Triage</span>
            <h1>Let’s talk about <span>careful review.</span></h1>
            <p>
              Inquiries regarding forensic screening capabilities, enterprise integration, or incident evaluation. Connect directly with our engineering and verification team.
            </p>
          </div>
          <aside className="contact-hero__signal" aria-label="Security operations status">
            <span className="signal-badge">DISPATCH STATUS</span>
            <div className="signal-status-row">
              <span className="signal-pulse" aria-hidden="true" />
              <strong>Global Verification Desk Active</strong>
            </div>
            <span className="signal-note">End-to-end encrypted dispatch</span>
          </aside>
        </section>

        <section className="container contact-layout">
          {/* Left Side: Contact Form */}
          <div className="contact-form-panel">
            <div className="contact-panel-heading">
              <span className="contact-panel-icon" aria-hidden="true">✉</span>
              <div>
                <span className="section-kicker">Direct Inquiry</span>
                <span className="contact-panel-note">Send a secure inquiry to our engineering team</span>
              </div>
            </div>
            <h2>How can we assist you?</h2>
            <p className="contact-form-intro">
              Complete the inquiry form below. Inquiries are reviewed under strict confidentiality.
            </p>
            <ContactForm />
          </div>

          {/* Right Side: Redesigned High-Tech Operations & Verification Desk */}
          <aside className="contact-details-panel">
            <div className="contact-desk-card">
              <div className="contact-panel-heading">
                <span className="contact-panel-icon contact-panel-icon--shield" aria-hidden="true">🛡</span>
                <div>
                  <span className="section-kicker">Security Operations</span>
                  <span className="contact-panel-note">Channels & Verification Protocols</span>
                </div>
              </div>

              <h3>Verification Desk SLA</h3>
              <p className="contact-details-intro">
                Our verification and forensic triage desks operate under dedicated response tier standards.
              </p>

              <div className="sla-grid">
                <div className="sla-box">
                  <span className="sla-label">CRITICAL TRIAGE</span>
                  <strong>&lt; 15 min</strong>
                  <small>Active forensic response</small>
                </div>
                <div className="sla-box">
                  <span className="sla-label">ENTERPRISE DESK</span>
                  <strong>24 / 7 / 365</strong>
                  <small>Priority engineering tier</small>
                </div>
              </div>

              <div className="contact-channels-list">
                <div className="channel-item">
                  <div className="channel-icon">◈</div>
                  <div className="channel-info">
                    <strong>Forensic Research & Analysis</strong>
                    <span>research@cgs-shield.internal</span>
                  </div>
                </div>
                <div className="channel-item">
                  <div className="channel-icon">✦</div>
                  <div className="channel-info">
                    <strong>Security & Vulnerability Disclosure</strong>
                    <span>security@cgs-shield.internal</span>
                  </div>
                </div>
                <div className="channel-item">
                  <div className="channel-icon">⌑</div>
                  <div className="channel-info">
                    <strong>Enterprise & Government Integrations</strong>
                    <span>solutions@cgs-shield.internal</span>
                  </div>
                </div>
              </div>

              <div className="contact-pgp-box">
                <div className="pgp-header">
                  <span className="pgp-icon">🔒</span>
                  <span className="pgp-title">PGP SECURE COMMUNICATIONS</span>
                </div>
                <code className="pgp-fingerprint">
                  4E18 9B02 D78A 3F11 50C9 E42B 88D1 77A4
                </code>
                <small className="pgp-note">Verified SHA-256 fingerprint for sensitive evidence transmission</small>
              </div>

              <div className="contact-guarantee-row">
                <span className="guarantee-dot" aria-hidden="true" />
                <span>Zero-Retention Privacy · No third-party data transmission</span>
              </div>
            </div>
          </aside>
        </section>
      </main>
      <Footer />
    </>
  );
}

