"use client";

import { createContext, useCallback, useContext, useEffect, useState, type FormEvent, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { api } from "@/lib/api";

export type AccountAccessStatus = {
  is_authenticated: boolean;
  email_verified: boolean;
  requires_email_verification: boolean;
  can_analyze: boolean;
  access_restricted: boolean;
  reference_id: string | null;
  contact_email: string | null;
};

type AccountAccessValue = {
  status: AccountAccessStatus | null;
  loading: boolean;
  refresh: () => Promise<AccountAccessStatus | null>;
};

const AccountAccessContext = createContext<AccountAccessValue>({
  status: null,
  loading: true,
  refresh: async () => null,
});

export function useAccountAccess() {
  return useContext(AccountAccessContext);
}

export function AccountAccessProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AccountAccessStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const pathname = usePathname();

  const refresh = useCallback(async () => {
    try {
      const next = await api<AccountAccessStatus>("/account/status");
      setStatus(next);
      return next;
    } catch {
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const handleRefresh = () => void refresh();
    window.addEventListener("cgs:account-refresh", handleRefresh);
    window.addEventListener("cgs:auth-success", handleRefresh);
    return () => {
      window.removeEventListener("cgs:account-refresh", handleRefresh);
      window.removeEventListener("cgs:auth-success", handleRefresh);
    };
  }, [refresh, pathname]);

  return (
    <AccountAccessContext.Provider value={{ status, loading, refresh }}>
      <AccessNotice />
      {children}
    </AccountAccessContext.Provider>
  );
}

function AccessNotice() {
  const { status, loading } = useAccountAccess();
  const pathname = usePathname();
  const [resending, setResending] = useState(false);
  const [copyState, setCopyState] = useState("");
  const [requestState, setRequestState] = useState("");

  async function resendVerification() {
    setResending(true);
    try {
      await api("/auth/resend-verification", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ return_to: pathname || "/app" }),
      });
      setCopyState("Verification email sent.");
    } catch (error) {
      setCopyState(error instanceof Error ? error.message : "The verification email could not be sent.");
    } finally {
      setResending(false);
    }
  }

  async function copyReference() {
    if (!status?.reference_id) return;
    try {
      await navigator.clipboard.writeText(status.reference_id);
      setCopyState("Reference ID copied.");
    } catch {
      setCopyState("Copy is unavailable. Select the reference ID to copy it.");
    }
  }

  async function requestUnblock(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!status?.reference_id) return;
    const form = event.currentTarget;
    setRequestState("");
    const values = new FormData(form);
    try {
      await api("/support/unblock-request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reference_id: status.reference_id,
          name: String(values.get("name") ?? "").trim(),
          email: String(values.get("email") ?? "").trim(),
          reason: String(values.get("reason") ?? "").trim(),
          website: String(values.get("website") ?? ""),
        }),
      });
      setRequestState("Your request has been saved for review.");
      form.reset();
    } catch (error) {
      setRequestState(error instanceof Error ? error.message : "The request could not be saved.");
    }
  }

  if (loading && !status) return null;
  if (!status || (!status.access_restricted && !status.requires_email_verification)) return null;

  return (
    <aside className={`access-widget${status.access_restricted ? " access-widget-restricted" : ""}`} aria-live="polite">
      {status.access_restricted ? (
        <div className="access-restriction" role="alert">
          <h2>Access restricted</h2>
          <p>Analysis access is restricted for this network. If you think this is a mistake, contact the CGS platform owner.</p>
          <div className="access-reference-row">
            <code>{status.reference_id}</code>
            <button type="button" className="access-text-button" onClick={copyReference}>Copy reference</button>
          </div>
          {status.contact_email && (
            <a
              className="access-action-link"
              href={`mailto:${status.contact_email}?subject=${encodeURIComponent(`Access review ${status.reference_id}`)}&body=${encodeURIComponent(`Please review this access restriction. Reference ID: ${status.reference_id}`)}`}
            >Contact CGS Owner</a>
          )}
          <form className="access-unblock-form" onSubmit={requestUnblock}>
            <strong>Request access review</strong>
            <label>Name<input name="name" autoComplete="name" required maxLength={100} /></label>
            <label>Email<input name="email" type="email" autoComplete="email" required maxLength={320} /></label>
            <label>Reason<textarea name="reason" required minLength={10} maxLength={1000} rows={3} /></label>
            <label className="access-honeypot" aria-hidden="true">Website<input name="website" tabIndex={-1} autoComplete="off" /></label>
            <button type="submit" className="access-action-button">Send request</button>
            {requestState && <p className="access-form-state" role="status">{requestState}</p>}
          </form>
          {copyState && <p className="access-form-state" role="status">{copyState}</p>}
        </div>
      ) : (
        <div className="access-widget-message">
          <p>Verify your email to run analyses on this account.</p>
          <button type="button" className="access-action-button" onClick={resendVerification} disabled={resending}>
            {resending ? "Sending…" : "Resend verification email"}
          </button>
          {copyState && <p className="access-form-state" role="status">{copyState}</p>}
        </div>
      )}
    </aside>
  );
}
