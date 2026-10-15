"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { Brand } from "@/components/brand";
import { ThemeToggle } from "@/components/theme-toggle";
import { api } from "@/lib/api";

export function AdminInviteForm() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const url = new URL(window.location.href);
    const invitationToken = url.searchParams.get("token") ?? "";
    setToken(invitationToken);
    if (invitationToken) {
      url.searchParams.delete("token");
      window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
    }
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setError("");
    if (!token) {
      setError("This invitation link is missing its one-time token. Ask an administrator to send a new invitation.");
      return;
    }

    const values = new FormData(event.currentTarget);
    const displayName = String(values.get("display_name") ?? "").trim();
    const username = String(values.get("username") ?? "").trim();
    const phoneNumber = String(values.get("phone_number") ?? "").trim();
    const password = String(values.get("password") ?? "");
    const confirmation = String(values.get("password_confirmation") ?? "");
    if (!displayName) return setError("Enter your name to continue.");
    if (!/^[A-Za-z0-9_]{3,32}$/.test(username)) return setError("Choose a username with 3–32 letters, numbers, or underscores.");
    if (!/^\+[1-9][0-9]{7,14}$/.test(phoneNumber)) return setError("Enter a complete phone number in international format, such as +923001234567.");
    if (password.length < 15) return setError("Choose a password with at least 15 characters.");
    if (password !== confirmation) return setError("The passwords do not match.");

    setBusy(true);
    try {
      await api("/auth/admin-invite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, display_name: displayName, username, phone_number: phoneNumber, password }),
      });
      router.replace("/admin");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to accept this administrator invitation.");
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <header className="auth-top">
        <Brand light />
        <div className="auth-top-actions">
          <Link className="button button-secondary auth-back" href="/admin/login">Administrator sign in</Link>
          <ThemeToggle />
        </div>
      </header>
      <main className="auth-main" aria-labelledby="admin-invite-title">
        <section className="auth-card auth-card-signup" aria-busy={busy}>
          <span className="auth-eyebrow">SECURE STAFF ACCESS</span>
          <h1 id="admin-invite-title">Accept your invitation</h1>
          <p className="auth-description">Create your administrator account using the one-time invitation link. This invitation expires after 24 hours.</p>
          <form className="auth-form admin-invite-auth-form" onSubmit={submit}>
            <div className="auth-field"><label htmlFor="admin-invite-name">Full name</label><input id="admin-invite-name" name="display_name" type="text" autoComplete="name" maxLength={80} required /></div>
            <div className="auth-field"><label htmlFor="admin-invite-username">Username</label><input id="admin-invite-username" name="username" type="text" autoComplete="username" minLength={3} maxLength={32} pattern="[A-Za-z0-9_]{3,32}" required /><small className="auth-field-hint">3–32 letters, numbers, or underscores.</small></div>
            <div className="auth-field"><label htmlFor="admin-invite-phone">Phone number</label><input id="admin-invite-phone" name="phone_number" type="tel" autoComplete="tel" inputMode="tel" placeholder="+923001234567" pattern="\+[1-9][0-9]{7,14}" maxLength={16} required /></div>
            <div className="auth-field"><label htmlFor="admin-invite-password">Password</label><input id="admin-invite-password" name="password" type="password" autoComplete="new-password" minLength={15} maxLength={128} required /><small className="auth-field-hint">Use at least 15 characters.</small></div>
            <div className="auth-field"><label htmlFor="admin-invite-confirmation">Confirm password</label><input id="admin-invite-confirmation" name="password_confirmation" type="password" autoComplete="new-password" minLength={15} maxLength={128} required /></div>
            {error && <p className="auth-error" role="alert">{error}</p>}
            <button className="auth-submit" type="submit" disabled={busy}>{busy ? <><span className="auth-spinner" aria-hidden="true" />Creating account…</> : "Create administrator account"}</button>
          </form>
          <p className="auth-switch"><Link href="/admin/login">Return to administrator sign in</Link></p>
        </section>
      </main>
      <footer className="auth-footer"><span>One-time invitation · Encrypted connection required</span><span>© {new Date().getFullYear()} CGS DeepFake Shield</span></footer>
    </div>
  );
}
