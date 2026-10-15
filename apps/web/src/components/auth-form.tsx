"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import { motion } from "motion/react";
import { Brand, Mark } from "@/components/brand";
import { SmoothInput } from "@/components/smooth-input";
import { Tooltip } from "@/components/tooltip";
import { ThemeToggle } from "@/components/theme-toggle";
import { PhoneInput } from "@/components/phone-input";
import { api, type User } from "@/lib/api";
import { isSafeLocalPath } from "@/lib/navigation";

export function AuthForm({ mode, audience = "user" }: { mode: "login" | "signup"; audience?: "user" | "admin" }) {
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [registrationEnabled, setRegistrationEnabled] = useState(true);
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [passwordValue, setPasswordValue] = useState("");
  const [failedAttempts, setFailedAttempts] = useState(0);
  const [lockoutTimer, setLockoutTimer] = useState(0);
  const router = useRouter();
  const signup = mode === "signup";
  const administrator = audience === "admin";
  const formTitle = administrator ? "Administrator sign in" : signup ? "Create your account" : "Welcome back";
  const formDescription = administrator
    ? "Zero-trust control plane. Cryptographically verified access for designated system owners."
    : signup
      ? "Join CGS DeepFake Shield to inspect and secure image evidence."
      : "Sign in to access your private inspection reports.";
  const formId = administrator ? "admin-auth" : signup ? "signup" : "signin";

  const passwordStrength = [
    passwordValue.length >= 8,
    passwordValue.length >= 15,
    /[a-z]/.test(passwordValue) && /[A-Z]/.test(passwordValue),
    /\d/.test(passwordValue),
    /[^A-Za-z0-9]/.test(passwordValue),
  ].filter(Boolean).length;
  const passwordMeterValue = passwordValue.length < 8 ? 0 : passwordStrength;
  const strengthLabel = passwordValue.length < 8 ? "Too short" : ["Very weak", "Weak", "Fair", "Strong", "Very strong"][Math.max(0, passwordStrength - 1)];
  const strengthLevel = passwordValue.length < 8 ? "weak" : ["very-weak", "weak", "fair", "strong", "very-strong"][Math.max(0, passwordStrength - 1)];

  useEffect(() => {
    if (signup) {
      api<{ registration_enabled?: boolean }>("/config")
        .then((config) => setRegistrationEnabled(config.registration_enabled ?? true))
        .catch(() => undefined);
      return;
    }
    if (typeof window !== "undefined") {
      const registered = new URLSearchParams(window.location.search).get("registered");
      if (registered === "1") {
        setNotice("Your account is ready. Verify your email to start analyzing media.");
      }
    }
  }, [signup]);

  useEffect(() => {
    if (lockoutTimer <= 0) return;
    const interval = setInterval(() => {
      setLockoutTimer((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [lockoutTimer]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || lockoutTimer > 0) return;
    if (signup && !registrationEnabled) {
      setError("New account registration is temporarily paused. Please check back later.");
      return;
    }

    const values = new FormData(event.currentTarget);
    const email = String(values.get("email") ?? "").trim();
    const password = String(values.get("password") ?? "");
    const passwordConfirm = String(values.get("password_confirm") ?? "");
    const displayName = String(values.get("display_name") ?? "").trim();
    const username = String(values.get("username") ?? "").trim();
    const phone = String(values.get("phone_number") ?? "").replace(/\D/g, "");
    const countryCode = String(values.get("phone_country") ?? "92");

    if (signup && !displayName) {
      setError("Please enter your full name.");
      return;
    }
    if (signup && !/^[A-Za-z0-9_]{3,32}$/.test(username)) {
      setError("Choose a username with 3–32 letters, numbers, or underscores.");
      return;
    }
    if (signup && password !== passwordConfirm) {
      setError("Passwords do not match. Please verify your confirm password field.");
      return;
    }
    if (signup && (phone.length < 7 || phone.length + countryCode.length > 15)) {
      setError("Please enter a valid phone number (at least 7 digits).");
      return;
    }

    setBusy(true);
    setError("");
    setNotice("");

    const payload: Record<string, string> = { email, password };
    if (signup) {
      payload.display_name = displayName;
      payload.username = username;
      payload.phone_number = `+${countryCode}${phone}`;
      const requestedNext = new URLSearchParams(window.location.search).get("next");
      payload.return_to = isSafeLocalPath(requestedNext) ? requestedNext : "/app";
    }

    try {
      const user = await api<User>(`/auth/${signup ? "signup" : "login"}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (signup) {
        window.dispatchEvent(new Event("cgs:auth-success"));
        const next = new URLSearchParams(window.location.search).get("next");
        const safeNext = isSafeLocalPath(next) ? next : "/app";
        router.replace(`/verify-email?next=${encodeURIComponent(safeNext)}`);
        return;
      }

      if (administrator && user.role !== "admin") {
        await api<void>("/auth/logout", { method: "POST" }).catch(() => undefined);
        throw new Error("This account does not have administrator access.");
      }

      setFailedAttempts(0);
      if (!administrator) window.dispatchEvent(new Event("cgs:auth-success"));
      const next = new URLSearchParams(window.location.search).get("next");
      const defaultPath = administrator ? "/admin" : "/app";
      const safeNext = isSafeLocalPath(next) && (!administrator || next.startsWith("/admin"));
      router.replace(safeNext && next ? next : defaultPath);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to sign in.";
      setError(message);
      setBusy(false);

      // Client-side brute-force mitigation & warning
      const nextAttempts = failedAttempts + 1;
      setFailedAttempts(nextAttempts);
      if (nextAttempts >= 5) {
        setLockoutTimer(30);
        setError("Too many consecutive attempts. Please wait 30 seconds before trying again.");
      }
    }
  }

  return (
    <div className={`auth-page${administrator ? " auth-page-admin" : ""}`}>
      <header className="auth-top">
        <Brand light />
        <div className="auth-top-actions">
          <Link className="button button-secondary auth-back" href="/" aria-label="Back to home">
            <span aria-hidden="true">←</span> Back to home
          </Link>
          <ThemeToggle />
        </div>
      </header>

      <main className="auth-main" aria-labelledby={`${formId}-title`}>
        <div className="auth-layout">
          <motion.aside
            className={`auth-visual${administrator ? " auth-visual-admin" : ""}`}
            aria-label={administrator ? "Administrator security overview" : "CGS image inspection report preview"}
            initial={{ opacity: 0, x: -18 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.34, ease: "easeOut" }}
          >
            {administrator ? (
              <div className="admin-command-panel">
                <div className="admin-command-header">
                  <div className="admin-status-badge">
                    <span className="admin-pulse-dot" />
                    <span>RESTRICTED GATEWAY · LEVEL 4</span>
                  </div>
                  <span className="admin-gate-secure-pill">TLS 1.3 / ENCRYPTED</span>
                </div>

                <div className="admin-hero-centerpiece">
                  <div className="admin-shield-emblem">
                    <div className="shield-ring shield-ring--outer" />
                    <div className="shield-ring shield-ring--middle" />
                    <div className="shield-core">
                      <Mark small />
                    </div>
                  </div>
                  <h2>Control Plane<br /><em>Zero-Trust Enclave</em></h2>
                  <p>Cryptographically isolated gateway. Every administrative action is audited, signed, and enforced by server policies.</p>
                </div>

                <div className="admin-telemetry-grid">
                  <div className="telemetry-box">
                    <span className="telemetry-label">SECURITY PROTOCOL</span>
                    <strong>ARGON2ID + HMAC</strong>
                    <small>Resistant to GPU / ASIC brute-force</small>
                  </div>
                  <div className="telemetry-box">
                    <span className="telemetry-label">DEFENSE RADAR</span>
                    <strong>ACTIVE MITIGATION</strong>
                    <small>Dynamic anti-automation shielding</small>
                  </div>
                  <div className="telemetry-box">
                    <span className="telemetry-label">AUDIT VERIFICATION</span>
                    <strong>IMMUTABLE LOGS</strong>
                    <small>Continuous telemetry recording</small>
                  </div>
                  <div className="telemetry-box">
                    <span className="telemetry-label">GATEWAY SLUG</span>
                    <strong>CRYPTOGRAPHIC TOKEN</strong>
                    <small>Obfuscated isolated endpoint</small>
                  </div>
                </div>

                <div className="admin-terminal-feed" aria-hidden="true">
                  <div className="terminal-top">
                    <span className="terminal-dot red" />
                    <span className="terminal-dot yellow" />
                    <span className="terminal-dot green" />
                    <span className="terminal-title">GATEWAY CONSOLE</span>
                  </div>
                  <div className="terminal-code">
                    <p><span className="t-green">[GATEWAY_OK]</span> Secret gate slug verified</p>
                    <p><span className="t-cyan">[INTEGRITY]</span> Model weight hash check: SHA-256 PASS</p>
                    <p><span className="t-lime">[DEFENSE]</span> Zero-trust security policy enforced</p>
                    <p><span className="t-muted">[LISTENER]</span> Awaiting authenticated operator token…</p>
                  </div>
                </div>

                <p className="auth-visual__footnote">
                  Restricted access. Use a trusted private workstation and log out upon task completion.
                </p>
              </div>
            ) : (
              <div className="user-forensic-panel">
                <div className="user-forensic-header">
                  <div className="user-status-badge">
                    <span className="user-pulse-dot" />
                    <span>NEURAL FORENSICS · ENGINE v2.4</span>
                  </div>
                  <span className="user-gate-secure-pill">ZERO-RETENTION VAULT</span>
                </div>

                <div className="user-hero-centerpiece">
                  <div className="user-radar-emblem">
                    <div className="radar-ring radar-ring--outer" />
                    <div className="radar-ring radar-ring--middle" />
                    <div className="radar-sweep" />
                    <div className="radar-core">
                      <Mark small />
                    </div>
                  </div>
                  <h2>Multi-Spectral Forensics<br /><em>DeepFake Shield</em></h2>
                  <p>
                    Precision neural classification and forensic artifact screening. Every inspection extracts frequency spectrum drift, provenance signatures, and pixel continuity.
                  </p>
                </div>

                <div className="user-telemetry-grid">
                  <div className="telemetry-box">
                    <span className="telemetry-label">FREQUENCY ANALYSIS</span>
                    <strong>FFT / DCT DRIFT</strong>
                    <small>High-frequency GAN artifact detection</small>
                  </div>
                  <div className="telemetry-box">
                    <span className="telemetry-label">ORIGIN PROVENANCE</span>
                    <strong>C2PA & EXIF LOGS</strong>
                    <small>Cryptographic hardware manifest audit</small>
                  </div>
                  <div className="telemetry-box">
                    <span className="telemetry-label">FACIAL CONTINUITY</span>
                    <strong>DIFFUSION MARGINS</strong>
                    <small>Edge warping & blending seam analysis</small>
                  </div>
                  <div className="telemetry-box">
                    <span className="telemetry-label">PRIVACY PLEDGE</span>
                    <strong>ZERO-KNOWLEDGE</strong>
                    <small>Ephemeral memory, no external storage</small>
                  </div>
                </div>

                <div className="user-terminal-feed" aria-hidden="true">
                  <div className="terminal-top">
                    <span className="terminal-dot red" />
                    <span className="terminal-dot yellow" />
                    <span className="terminal-dot green" />
                    <span className="terminal-title">FORENSIC ENGINE STREAM</span>
                  </div>
                  <div className="terminal-code">
                    <p><span className="t-green">[SCANNER_OK]</span> Local ONNX neural forensic runtime active</p>
                    <p><span className="t-lime">[PRECISION]</span> 99.8% synthetic artifact sensitivity configured</p>
                    <p><span className="t-cyan">[PROVENANCE]</span> Cryptographic C2PA / JUMBF parser online</p>
                    <p><span className="t-muted">[SECURE_RAM]</span> Tenant-isolated ephemeral pipeline ready…</p>
                  </div>
                </div>

                <p className="auth-visual__footnote">
                  Reproducible image forensics and neural integrity screening for critical decision-makers.
                </p>
              </div>
            )}
          </motion.aside>

          <motion.section
            className={`auth-card${signup ? " auth-card-signup" : ""}`}
            aria-labelledby={`${formId}-title`}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.34, delay: 0.06, ease: "easeOut" }}
          >
            <span className="auth-eyebrow">
              {administrator ? "Restricted administrator access" : "Private image inspection"}
            </span>
            <h1 id={`${formId}-title`}>{formTitle}</h1>
            <p className="auth-description">{formDescription}</p>
            {signup && !registrationEnabled && (
              <div className="auth-lockout-notice" role="status">
                New account registration is temporarily paused. Please check back later.
              </div>
            )}

            <form
              className="auth-form"
              onSubmit={submit}
              aria-describedby={error ? `${formId}-error` : undefined}
              aria-busy={busy || lockoutTimer > 0}
            >
              {signup && (
                <div className="auth-field">
                  <label htmlFor={`${formId}-name`}>Full Name</label>
                  <SmoothInput
                    id={`${formId}-name`}
                    name="display_name"
                    type="text"
                    autoComplete="name"
                    placeholder="e.g. Jane Doe"
                    maxLength={80}
                    required
                    disabled={busy || lockoutTimer > 0}
                  />
                </div>
              )}

              {signup && (
                <div className="auth-field">
                  <label htmlFor={`${formId}-username`}>Username</label>
                  <SmoothInput
                    id={`${formId}-username`}
                    name="username"
                    type="text"
                    autoComplete="username"
                    minLength={3}
                    maxLength={32}
                    placeholder="e.g. janedoe_shield"
                    pattern="[A-Za-z0-9_]{3,32}"
                    title="Use 3–32 letters, numbers, or underscores."
                    autoCapitalize="none"
                    spellCheck={false}
                    required
                    disabled={busy || lockoutTimer > 0}
                  />
                  <small className="auth-field-hint">3–32 letters, numbers, or underscores</small>
                </div>
              )}

              {signup && (
                <div className="auth-field">
                  <label htmlFor={`${formId}-phone`}>Phone Number</label>
                  <PhoneInput
                    id={`${formId}-phone`}
                    name="phone_number"
                    countryName="phone_country"
                    defaultCountry="PK"
                    placeholder="300 123 4567"
                    required
                    disabled={busy || lockoutTimer > 0}
                  />
                  <small className="auth-field-hint">Select your country code from the dropdown</small>
                </div>
              )}

              <div className="auth-field">
                <label htmlFor={`${formId}-email`}>
                  {signup ? "Email Address" : "Email or Username"}
                </label>
                <SmoothInput
                  id={`${formId}-email`}
                  name="email"
                  type="text"
                  autoComplete={signup ? "email" : "username"}
                  autoCapitalize="none"
                  spellCheck={false}
                  placeholder={signup ? "name@company.com" : "Email or username"}
                  maxLength={320}
                  required
                  disabled={busy || lockoutTimer > 0}
                />
              </div>

              <div className="auth-field">
                <label htmlFor={`${formId}-password`}>Password</label>
                <div className="auth-password-wrap">
                  <SmoothInput
                    id={`${formId}-password`}
                    name="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete={signup ? "new-password" : "current-password"}
                    minLength={signup ? 15 : undefined}
                    maxLength={128}
                    placeholder={signup ? "Min. 15 characters" : "Enter your password"}
                    required
                    disabled={busy || lockoutTimer > 0}
                    onChange={(event: ChangeEvent<HTMLInputElement>) => setPasswordValue(event.currentTarget.value)}
                    aria-describedby={signup ? `${formId}-password-hint` : undefined}
                  />
                  <Tooltip label={showPassword ? "Hide password" : "Show password"}>
                    <button
                      className="auth-password-toggle"
                      type="button"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      aria-pressed={showPassword}
                      aria-controls={`${formId}-password`}
                      onClick={() => setShowPassword((visible) => !visible)}
                      disabled={busy || lockoutTimer > 0}
                    >
                      {showPassword ? (
                        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                          <path d="M3 3l18 18M10.6 10.7a2 2 0 0 0 2.7 2.7M9.9 5.2A10.5 10.5 0 0 1 12 5c5.2 0 8.5 4.2 9.5 7-.4 1.1-1.3 2.4-2.7 3.5M6.2 6.3C4.4 7.5 3.3 9.1 2.5 12c1 2.8 4.3 7 9.5 7 1.1 0 2.1-.2 3-.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      ) : (
                        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                          <path d="M2.5 12S6 5 12 5s9.5 7 9.5 7-3.5 7-9.5 7-9.5-7-9.5-7Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round"/>
                          <circle cx="12" cy="12" r="2.5" stroke="currentColor" strokeWidth="1.7"/>
                        </svg>
                      )}
                    </button>
                  </Tooltip>
                </div>
                {signup && (
                  <div id={`${formId}-password-hint`} className="auth-password-strength" data-level={strengthLevel} aria-live="polite">
                    <div className="auth-password-strength__meter" role="meter" aria-label="Password strength" aria-valuemin={0} aria-valuemax={5} aria-valuenow={passwordMeterValue}>
                      {Array.from({ length: 5 }, (_, index) => (
                        <span key={index} className={index < passwordMeterValue ? "is-active" : ""} />
                      ))}
                    </div>
                    <span>{passwordValue ? `Password strength: ${strengthLabel}` : "Use at least 15 characters."}</span>
                  </div>
                )}
              </div>

              {!signup && !administrator && (
                <p className="auth-recovery-link"><Link href="/forgot-password">Forgot your password?</Link></p>
              )}

              {signup && (
                <div className="auth-field">
                  <label htmlFor={`${formId}-confirm-password`}>Confirm Password</label>
                  <div className="auth-password-wrap">
                    <SmoothInput
                      id={`${formId}-confirm-password`}
                      name="password_confirm"
                      type={showPassword ? "text" : "password"}
                      autoComplete="new-password"
                      minLength={15}
                      maxLength={128}
                      placeholder="Re-enter your password"
                      required
                      disabled={busy || lockoutTimer > 0}
                    />
                    <Tooltip label={showPassword ? "Hide password" : "Show password"}>
                      <button
                        className="auth-password-toggle"
                        type="button"
                        aria-label={showPassword ? "Hide password" : "Show password"}
                        aria-pressed={showPassword}
                        aria-controls={`${formId}-confirm-password`}
                        onClick={() => setShowPassword((visible) => !visible)}
                        disabled={busy || lockoutTimer > 0}
                      >
                        {showPassword ? (
                          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                            <path d="M3 3l18 18M10.6 10.7a2 2 0 0 0 2.7 2.7M9.9 5.2A10.5 10.5 0 0 1 12 5c5.2 0 8.5 4.2 9.5 7-.4 1.1-1.3 2.4-2.7 3.5M6.2 6.3C4.4 7.5 3.3 9.1 2.5 12c1 2.8 4.3 7 9.5 7 1.1 0 2.1-.2 3-.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                        ) : (
                          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                            <path d="M2.5 12S6 5 12 5s9.5 7 9.5 7-3.5 7-9.5 7-9.5-7-9.5-7Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round"/>
                            <circle cx="12" cy="12" r="2.5" stroke="currentColor" strokeWidth="1.7"/>
                          </svg>
                        )}
                      </button>
                    </Tooltip>
                  </div>
                </div>
              )}

              {notice && (
                <div className="auth-notice-banner" role="status">
                  <span className="notice-icon" aria-hidden="true">✓</span>
                  <div>
                    <strong>Action Required:</strong>
                    <p>{notice}</p>
                  </div>
                </div>
              )}

              {error && (
                <div id={`${formId}-error`} className="auth-error-banner" role="alert">
                  <span className="error-icon" aria-hidden="true">!</span>
                  <div>
                    <strong>Attention</strong>
                    <p>{error}</p>
                  </div>
                </div>
              )}

              {lockoutTimer > 0 && (
                <div className="auth-lockout-notice" role="alert">
                  <span>⏱</span> Security pause: try again in {lockoutTimer}s
                </div>
              )}

              <button
                className="button button-primary button-wide auth-submit btn-lime-themed"
                type="submit"
                disabled={busy || lockoutTimer > 0 || (signup && !registrationEnabled)}
              >
                {busy && <span className="auth-spinner" aria-hidden="true" />}
                <span>
                  {busy
                    ? signup
                      ? "Creating account…"
                      : "Verifying credentials…"
                    : lockoutTimer > 0
                      ? `Locked (${lockoutTimer}s)`
                      : signup
                        ? "Create account"
                        : administrator
                          ? "Sign in to admin"
                          : "Sign in"}
                </span>
              </button>
            </form>

            {!administrator && (
              <p className="auth-switch">
                {signup ? (
                  <>
                    Already have an account?{" "}
                    <Link href="/login" className="auth-switch-link">
                      Sign in
                    </Link>
                  </>
                ) : (
                  <>
                    New to CGS DeepFake Shield?{" "}
                    <Link href="/register" className="auth-switch-link">
                      Create an account
                    </Link>
                  </>
                )}
              </p>
            )}
          </motion.section>
        </div>
      </main>

      {administrator ? (
        <footer className="auth-footer auth-admin-note">
          Security clearance required. System sessions and cryptographic assertions are validated continuously.
        </footer>
      ) : (
        <footer className="auth-footer">
          <span>Your reports are private to your account.</span>
          <Link href="/privacy">Read our privacy details</Link>
        </footer>
      )}
    </div>
  );
}
