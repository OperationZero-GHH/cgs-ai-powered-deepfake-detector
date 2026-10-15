"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { Brand } from "@/components/brand";
import { api } from "@/lib/api";
import { isSafeLocalPath } from "@/lib/navigation";
import { useAccountAccess } from "@/components/account-access-context";

type RecoveryMode = "verify" | "forgot" | "reset";

export function AccountRecovery({ mode }: { mode: RecoveryMode }) {
  const { refresh } = useAccountAccess();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [verified, setVerified] = useState(false);
  const [resetDone, setResetDone] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [token, setToken] = useState("");
  const [nextPath, setNextPath] = useState("/app");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const requestedNext = params.get("next");
    const safeNext = isSafeLocalPath(requestedNext) ? requestedNext : "/app";
    setNextPath(safeNext);
    const linkToken = params.get("token") ?? "";
    setToken(linkToken);
    if (mode !== "verify" || !linkToken) return;

    let active = true;
    setBusy(true);
    api<{ verified: boolean }>("/auth/verify-email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: linkToken }),
    })
      .then(async () => {
        if (!active) return;
        setVerified(true);
        setNotice("Your email is verified. Your account is ready to analyze media.");
        window.dispatchEvent(new Event("cgs:auth-success"));
        window.dispatchEvent(new Event("cgs:account-refresh"));
        await refresh();
        const cleanUrl = new URLSearchParams({ verified: "1", next: safeNext });
        router.replace(`/verify-email?${cleanUrl.toString()}`);
      })
      .catch((reason) => {
        if (active) setError(reason instanceof Error ? reason.message : "This verification link is invalid or expired.");
      })
      .finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [mode, refresh, router]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const values = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    setNotice("");
    try {
      if (mode === "forgot") {
        await api("/auth/forgot-password", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: String(values.get("email") ?? "").trim(), return_to: nextPath }),
        });
        setNotice("If that account exists, password reset instructions have been sent.");
      } else if (mode === "reset") {
        const password = String(values.get("password") ?? "");
        const confirm = String(values.get("confirm") ?? "");
        if (password !== confirm) throw new Error("Passwords do not match.");
        if (password.length < 15) throw new Error("Use at least 15 characters for your password.");
        if (!token) throw new Error("This password reset link is missing its token.");
        await api("/auth/reset-password", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token, password }),
        });
        setResetDone(true);
        setNotice("Your password has been changed. Sign in with the new password.");
      } else {
        await api("/auth/resend-verification", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ return_to: nextPath }),
        });
        setNotice("A fresh verification link has been sent.");
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The request could not be completed.");
    } finally {
      setBusy(false);
    }
  }

  const titles = {
    verify: verified ? "Email verified" : "Verify your email",
    forgot: "Reset your password",
    reset: resetDone ? "Password updated" : "Choose a new password",
  };
  const descriptions = {
    verify: verified
      ? "Your account is verified and ready to analyze media."
      : "Check your inbox for the one-time verification link to finish setting up your account.",
    forgot: "Enter the email address linked to your account. If it exists, we’ll send a one-time reset link.",
    reset: "Choose a new password with at least 15 characters. This will sign out your other sessions.",
  };

  return (
    <div className="auth-page">
      <header className="auth-top"><Brand light /></header>
      <main className="auth-main">
        <section className="auth-card recovery-card" aria-labelledby="recovery-title">
          <span className="auth-eyebrow">Account security</span>
          <h1 id="recovery-title">{titles[mode]}</h1>
          <p className="auth-description">{descriptions[mode]}</p>

          {mode === "verify" && !verified && !token && (
            <form className="auth-form" onSubmit={submit}>
              <button type="submit" className="auth-submit" disabled={busy}>
                {busy ? "Sending…" : "Resend verification email"}
              </button>
            </form>
          )}

          {mode === "verify" && busy && token && <p role="status" className="recovery-message">Verifying your email…</p>}

          {mode === "forgot" && (
            <form className="auth-form" onSubmit={submit}>
              <div className="auth-field">
                <label htmlFor="forgot-email">Email address</label>
                <input id="forgot-email" name="email" type="email" autoComplete="email" maxLength={320} required disabled={busy} />
              </div>
              <button type="submit" className="auth-submit" disabled={busy}>{busy ? "Sending…" : "Send reset link"}</button>
            </form>
          )}

          {mode === "reset" && !resetDone && (
            token ? (
              <form className="auth-form" onSubmit={submit}>
                <div className="auth-field">
                  <label htmlFor="reset-password">New password</label>
                  <input id="reset-password" name="password" type={showPassword ? "text" : "password"} autoComplete="new-password" minLength={15} maxLength={128} required disabled={busy} />
                  <small className="auth-field-hint">At least 15 characters. Do not reuse a password from another site.</small>
                </div>
                <div className="auth-field">
                  <label htmlFor="reset-confirm">Confirm password</label>
                  <input id="reset-confirm" name="confirm" type={showPassword ? "text" : "password"} autoComplete="new-password" minLength={15} maxLength={128} required disabled={busy} />
                </div>
                <label className="recovery-show-password"><input type="checkbox" checked={showPassword} onChange={(event) => setShowPassword(event.currentTarget.checked)} /> Show password</label>
                <button type="submit" className="auth-submit" disabled={busy}>{busy ? "Updating…" : "Update password"}</button>
              </form>
            ) : <p role="alert" className="auth-error-banner">This reset link is missing its token. Request a new one below.</p>
          )}

          {notice && <p role="status" aria-live="polite" className="recovery-message">{notice}</p>}
          {error && <p role="alert" className="auth-error-banner">{error}</p>}

          {mode === "verify" && verified && <Link className="auth-submit recovery-continue" href={nextPath}>Continue</Link>}
          {mode === "reset" && resetDone && <Link className="auth-submit recovery-continue" href="/login">Sign in</Link>}
          {mode === "reset" && !token && <Link className="auth-submit recovery-continue" href="/forgot-password">Request a new link</Link>}
          {mode === "forgot" && <Link className="auth-submit recovery-continue" href={`/login?next=${encodeURIComponent(nextPath)}`}>Return to sign in</Link>}
          {mode === "verify" && !verified && <Link className="recovery-secondary-link" href={`/login?next=${encodeURIComponent(nextPath)}`}>Back to sign in</Link>}
        </section>
      </main>
    </div>
  );
}
