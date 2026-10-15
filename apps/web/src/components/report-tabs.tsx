"use client";

import { useState } from "react";

const defaultTab = "limits";

const tabs = [
  { id: "integrity", label: "Integrity", heading: "Integrity", summary: "File validity, dimensions, and hash remain observable facts." },
  { id: "metadata", label: "Metadata", heading: "Metadata", summary: "EXIF and ICC signals are contextual clues, not proof." },
  { id: "provenance", label: "Provenance", heading: "Provenance", summary: "C2PA and authenticity signals require an explicit verifier." },
  { id: "synthetic", label: "Synthetic-image", heading: "Synthetic-image", summary: "Model outputs only matter when the model is valid, documented, and calibrated." },
  { id: "manipulation", label: "Manipulation", heading: "Manipulation", summary: "Localized edits and face swaps need separate, specialized evidence." },
  { id: "limits", label: "Limits", heading: "Limits", summary: "The current product keeps uncertainty visible and remains inconclusive when the method is unavailable." },
] as const;

export function ReportTabs() {
  const [active, setActive] = useState<(typeof tabs)[number]["id"]>(defaultTab);

  const current = tabs.find((tab) => tab.id === active) ?? tabs[0];

  return (
    <div className="report-tabs" aria-label="Report section details">
      <div className="tablist" role="tablist" aria-label="Report sections">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            id={`tab-${tab.id}`}
            aria-selected={active === tab.id}
            aria-controls={`panel-${tab.id}`}
            tabIndex={active === tab.id ? 0 : -1}
            className={active === tab.id ? "tab-button is-active" : "tab-button"}
            onClick={() => setActive(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div
        role="tabpanel"
        id={`panel-${current.id}`}
        aria-labelledby={`tab-${current.id}`}
        className="tab-panel"
      >
        <div className="tab-panel__header">
          <span className="section-kicker">{current.heading}</span>
          <h3>{current.summary}</h3>
        </div>

        <div className="tab-panel__content">
          {current.id === "integrity" && (
            <>
              <p>File integrity is verified through format checks, bounded decoding, and a SHA-256 reference. These are real findings, but they do not establish whether an image is authentic.</p>
              <ul className="checklist minimal-checklist">
                <li>Format validated: JPEG, PNG, WebP</li>
                <li>Dimensions and hash recorded</li>
                <li>Preview normalized for safe display</li>
              </ul>
            </>
          )}
          {current.id === "metadata" && (
            <>
              <p>EXIF and ICC metadata can reveal useful context about provenance and processing history, but their presence alone is not a verdict.</p>
              <ul className="checklist minimal-checklist">
                <li>EXIF: present</li>
                <li>ICC profile: absent</li>
                <li>Metadata signal is contextual, not declarative</li>
              </ul>
            </>
          )}
          {current.id === "provenance" && (
            <>
              <p>Provenance systems such as C2PA can attest to source history, provided a compatible verifier and valid credentials exist. This build does not configure that path.</p>
              <ul className="checklist minimal-checklist">
                <li>Status: Not configured</li>
                <li>Verifier unavailable</li>
                <li>Credentials are not treated as proof of depicted facts</li>
              </ul>
            </>
          )}
          {current.id === "synthetic" && (
            <>
              <p>AI-generated-image classification must be documented, calibrated, and operationally bounded. A score without those guardrails is just a model output, not an evidence claim.</p>
              <ul className="checklist minimal-checklist">
                <li>Model status: Unavailable</li>
                <li>Calibration and thresholds: not configured</li>
                <li>Score: not presented as probability</li>
              </ul>
            </>
          )}
          {current.id === "manipulation" && (
            <>
              <p>Localized edits and face swaps are distinct methods. A broad synthetic-image detector does not replace a manipulation-localization workflow.</p>
              <ul className="checklist minimal-checklist">
                <li>Face-swap indicators: not configured</li>
                <li>Localized edits: separate task</li>
                <li>Analysis remains scoped and skeptical</li>
              </ul>
            </>
          )}
          {current.id === "limits" && (
            <>
              <p>Inconclusive is a valid outcome. This report states what is known, what is missing, and which methods are unavailable. That honesty is the product.</p>
              <ul className="checklist minimal-checklist">
                <li>Overall result: Inconclusive</li>
                <li>Detector not configured</li>
                <li>Metadata alone cannot establish authenticity</li>
              </ul>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
