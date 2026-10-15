"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type User } from "@/lib/api";

export default function SettingsPage() {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const router = useRouter();

  useEffect(() => {
    api<User>("/auth/me")
      .then(setUser)
      .catch(() => {});
  }, []);

  const isAdmin = user?.role === "admin";

  async function remove() {
    if (!window.confirm("CRITICAL WARNING: Permanently delete your account, all image records, and SHA-256 evidence digests? This operation cannot be reversed.")) return;
    setBusy(true);
    setError("");
    try {
      await api<void>("/auth/account", { method: "DELETE" });
      router.replace("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to delete account.");
      setBusy(false);
    }
  }

  return (
    <div className="dashboard-content settings-page-content">
      {/* Top Banner */}
      <div className="dash-hero-banner settings-hero-banner">
        <div className="dash-hero-info">
          <div className="dash-hero-eyebrow">
            <span className="live-dot-pulse" aria-hidden="true" />
            <span>SECURITY CONTROL &amp; RETENTION VAULT</span>
          </div>
          <h1>Workspace &amp; Security Settings</h1>
          <p>
            Configure storage isolation policies, review cryptographic integrity protocols, and manage account destruction parameters.
          </p>
        </div>
      </div>

      <div className="settings-grid">
        {/* Section 1: Storage & Retention */}
        <section className="dash-panel settings-section-card">
          <div className="panel-header">
            <div>
              <h2>Storage &amp; Cryptographic Retention</h2>
              <p>Rules governing your uploaded image evidence and forensic reports.</p>
            </div>
            <span className="privacy-chip">
              <i aria-hidden="true" /> AES-256
            </span>
          </div>

          <div className="settings-items-list">
            <div className="settings-item">
              <div className="settings-item-info">
                <strong>Private Enclave Storage</strong>
                <small>Original images and normalized evidence crops are stored in private disk partitions with tenant-level isolation.</small>
              </div>
              <span className="setting-status-badge is-active">ENFORCED</span>
            </div>

            <div className="settings-item">
              <div className="settings-item-info">
                <strong>Data Retention Duration</strong>
                <small>Records remain securely preserved in your private ledger until you explicitly purge them. No automatic expiration.</small>
              </div>
              <span className="setting-status-badge is-active">PERSISTENT</span>
            </div>

            <div className="settings-item">
              <div className="settings-item-info">
                <strong>Immutable Evidence Hashing</strong>
                <small>A 64-character SHA-256 checksum is computed upon ingestion to ensure mathematical immutability.</small>
              </div>
              <span className="setting-status-badge is-active">SHA-256 PASS</span>
            </div>
          </div>
        </section>

        {/* Section 2: Security & Authentication Parameters */}
        <section className="dash-panel settings-section-card">
          <div className="panel-header">
            <div>
              <h2>Session &amp; Zero-Trust Governance</h2>
              <p>Cryptographic session security and access control policies.</p>
            </div>
            <span className="setting-tag">ACTIVE SESSION</span>
          </div>

          <div className="settings-items-list">
            <div className="settings-item">
              <div className="settings-item-info">
                <strong>Password Encryption Standard</strong>
                <small>Argon2id (time-cost 3, 64MB memory, 2 threads) + Peppered HMAC resistance against ASIC/GPU brute-force.</small>
              </div>
              <code className="setting-code-badge">ARGON2ID</code>
            </div>

            <div className="settings-item">
              <div className="settings-item-info">
                <strong>Row-Level Security (RLS)</strong>
                <small>Database transactions execute under tenant-restricted session principals. Cross-tenant leakage is mathematically impossible.</small>
              </div>
              <span className="setting-status-badge is-active">RLS GUARDED</span>
            </div>

            <div className="settings-item">
              <div className="settings-item-info">
                <strong>Persistent Worker Queue</strong>
                <small>Inference workloads execute in an isolated background thread pool with strict lease renewal.</small>
              </div>
              <span className="setting-status-badge is-active">WORKER ACTIVE</span>
            </div>
          </div>
        </section>

        {/* Section 3: Destruction Zone or Admin Immutability Shield */}
        {isAdmin ? (
          <section className="dash-panel settings-section-card" style={{ borderColor: "var(--accent)", borderWidth: 2, borderStyle: "solid" }}>
            <div className="panel-header">
              <div>
                <h2 style={{ color: "var(--accent)" }}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 22, height: 22, display: "inline-block", verticalAlign: "middle", marginRight: 8 }} aria-hidden="true">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                  Immutable Administrator Enclave
                </h2>
                <p>This administrator account is cryptographically locked. Credentials cannot be modified, deactivated, or deleted through the web application.</p>
              </div>
              <span className="setting-status-badge is-active" style={{ background: "var(--accent)", color: "#000", fontWeight: 700 }}>LOCKED</span>
            </div>

            <div className="settings-items-list">
              <div className="settings-item">
                <div className="settings-item-info">
                  <strong>Account Deletion</strong>
                  <small>Blocked by server-side immutability policy. Even with a valid session, the API will reject all DELETE requests targeting this account.</small>
                </div>
                <span className="setting-status-badge is-active" style={{ background: "var(--accent)", color: "#000" }}>BLOCKED</span>
              </div>

              <div className="settings-item">
                <div className="settings-item-info">
                  <strong>Credential Modification</strong>
                  <small>Password, email, username, and role changes are rejected at the API layer. Credential rotation requires direct database access.</small>
                </div>
                <span className="setting-status-badge is-active" style={{ background: "var(--accent)", color: "#000" }}>BLOCKED</span>
              </div>

              <div className="settings-item">
                <div className="settings-item-info">
                  <strong>Account Deactivation</strong>
                  <small>Deactivation is rejected even when requested by another administrator. All tampering attempts are logged to the audit ledger.</small>
                </div>
                <span className="setting-status-badge is-active" style={{ background: "var(--accent)", color: "#000" }}>BLOCKED</span>
              </div>
            </div>
          </section>
        ) : (
          <section className="dash-panel settings-danger-card">
            <div className="panel-header">
              <div>
                <h2 className="danger-heading">Permanent Account Destruction</h2>
                <p>Erase your operator identity, cryptographic digests, stored images, and inspection ledger.</p>
              </div>
              <span className="danger-badge">IRREVERSIBLE</span>
            </div>

            <div className="danger-box-content">
              <p>
                Executing this operation permanently purges all files from the disk partition, drops database row entries, and revokes active session credentials immediately. This action cannot be undone.
              </p>

              {error && (
                <div className="dash-error-state" role="alert">
                  <span className="alert-icon">!</span>
                  <div>
                    <strong>Purge error:</strong>
                    <p>{error}</p>
                  </div>
                </div>
              )}

              <button
                className="button danger-button settings-danger-btn"
                disabled={busy}
                onClick={() => void remove()}
                type="button"
              >
                {busy ? "Purging Account & Data…" : "Permanently Delete Account & All Data"}
              </button>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
