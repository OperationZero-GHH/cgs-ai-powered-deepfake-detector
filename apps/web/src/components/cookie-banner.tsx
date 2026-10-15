"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const CONSENT_KEY = "cgs-optional-cookie-choice";

export function CookieBanner() {
  const [ready, setReady] = useState(false);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setReady(true);

    const revealAfterAuthentication = () => {
      try {
        setVisible(window.localStorage.getItem(CONSENT_KEY) === null);
      } catch {
        setVisible(true);
      }
    };

    window.addEventListener("cgs:auth-success", revealAfterAuthentication);
    return () => window.removeEventListener("cgs:auth-success", revealAfterAuthentication);
  }, []);

  function choose(choice: "accepted" | "rejected") {
    try {
      window.localStorage.setItem(CONSENT_KEY, choice);
    } catch {
      // The banner still dismisses when browser storage is unavailable.
    }
    setVisible(false);
  }

  if (!ready || !visible) return null;

  return (
    <aside className="cookie-banner" aria-label="Cookie preferences">
      <div className="cookie-banner__copy">
        <strong>Cookie preferences</strong>
        <p>Essential session cookies support sign-in. Optional analytics are not configured.</p>
      </div>
      <div className="cookie-banner__actions">
        <button className="button button-secondary" type="button" onClick={() => choose("rejected")}>Reject</button>
        <button className="button button-primary" type="button" onClick={() => choose("accepted")}>Accept</button>
        <Link href="/privacy#cookies">Settings</Link>
      </div>
    </aside>
  );
}
