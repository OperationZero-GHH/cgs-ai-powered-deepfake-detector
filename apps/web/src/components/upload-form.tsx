"use client";

import { useEffect, useRef, useState, type DragEvent, type ChangeEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError, formatBytes, type Analysis } from "@/lib/api";
import { Tooltip } from "@/components/tooltip";
import { useAccountAccess } from "@/components/account-access-context";
import { verifyAssetType, type TypeVerificationResult } from "@/lib/type-verification";
import { NeuralScanOverlay } from "@/components/neural-scan-overlay";

const DEFAULT_MAX_BYTES = 50 * 1024 * 1024;
const ACCEPT = [
  "image/jpeg",
  "image/png",
  "image/webp",
  "video/mp4",
  "video/webm",
  "video/quicktime",
  "video/x-msvideo",
  "audio/wav",
  "audio/x-wav",
  "audio/mpeg",
  "audio/mp3",
  "audio/flac",
  "audio/x-flac",
  "audio/ogg",
  "audio/mp4",
  "audio/x-m4a",
  "audio/aac",
];

export function UploadForm() {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [preview, setPreview] = useState("");
  const [maxBytes, setMaxBytes] = useState(DEFAULT_MAX_BYTES);
  const [detectorStatus, setDetectorStatus] = useState("checking");
  const [inspectionsEnabled, setInspectionsEnabled] = useState(true);
  const [typeVerification, setTypeVerification] = useState<TypeVerificationResult | null>(null);
  const [verifyingType, setVerifyingType] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const { status, loading: accessLoading, refresh: refreshAccountAccess } = useAccountAccess();
  const isAuthenticated = Boolean(status?.is_authenticated);
  const canAnalyze = Boolean(status?.can_analyze && inspectionsEnabled);

  const isVideo = file?.type.startsWith("video/") || Boolean(file?.name.match(/\.(mp4|webm|mov|avi|mkv)$/i));
  const isAudio = file?.type.startsWith("audio/") || Boolean(file?.name.match(/\.(wav|mp3|flac|ogg|m4a|aac)$/i));

  useEffect(() => {
    if (!file) {
      setPreview("");
      return;
    }
    const previewUrl = URL.createObjectURL(file);
    setPreview(previewUrl);
    return () => URL.revokeObjectURL(previewUrl);
  }, [file]);

  useEffect(() => {
    api<{ max_upload_bytes: number; max_video_bytes?: number; detector?: { status: string }; inspections_enabled?: boolean }>("/config")
      .then((config) => {
        setMaxBytes(config.max_video_bytes ?? config.max_upload_bytes ?? DEFAULT_MAX_BYTES);
        setDetectorStatus(config.detector?.status ?? "unavailable");
        setInspectionsEnabled(config.inspections_enabled ?? true);
      })
      .catch(() => setDetectorStatus("unavailable"));
  }, []);

  const maxLabel =
    maxBytes % (1024 * 1024) === 0 ? `${maxBytes / (1024 * 1024)} MB` : formatBytes(maxBytes);

  async function choose(candidate?: File) {
    setError("");
    if (!canAnalyze) return;
    if (!candidate) return;
    const isSupported =
      ACCEPT.includes(candidate.type) ||
      Boolean(candidate.name.match(/\.(jpe?g|png|webp|mp4|webm|mov|avi|mkv|wav|mp3|flac|ogg|m4a|aac)$/i));
    if (!isSupported) {
      setError("Upload a supported format: JPEG, PNG, WebP, MP4, WebM, MOV, WAV, MP3, FLAC, or OGG.");
      setTypeVerification(null);
      return;
    }
    if (candidate.size > maxBytes) {
      setError(`This media file is larger than the ${maxLabel} limit.`);
      setTypeVerification(null);
      return;
    }

    setVerifyingType(true);
    try {
      const verified = await verifyAssetType(candidate);
      setTypeVerification(verified);
      if (!verified.verified) {
        setError(verified.message);
        setFile(null);
        return;
      }
      setFile(candidate);
    } catch {
      setFile(candidate);
    } finally {
      setVerifyingType(false);
    }
  }

  function onInput(event: ChangeEvent<HTMLInputElement>) {
    choose(event.target.files?.[0]);
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    choose(event.dataTransfer.files?.[0]);
  }

  async function submit() {
    if (!canAnalyze) {
      setError(status?.access_restricted
        ? "Analysis access is restricted for this network. Review the access notice above."
        : status?.requires_email_verification
          ? "Verify your email before running an analysis."
          : "Analysis is unavailable. Refresh the page or sign in to continue.");
      return;
    }
    if (!file || busy) return;
    setBusy(true);
    setError("");
    const body = new FormData();
    body.set("file", file);
    try {
      const idempotencyKey = crypto.randomUUID();
      const analysis = await api<Analysis>("/analyses", {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
        body,
      });
      window.dispatchEvent(new Event("cgs:account-refresh"));
      router.push(`/app/analyses/${analysis.analysis_id}`);
    } catch (err) {
      const nextStatus = await refreshAccountAccess();
      if (err instanceof ApiError && err.code === "EMAIL_NOT_VERIFIED") {
        setError("Verify your email before running an analysis.");
      } else if (err instanceof ApiError && err.code === "IP_ACCOUNT_LIMIT") {
        setError(`Analysis access is restricted. Reference: ${err.referenceId ?? "Contact support."}`);
      } else {
        setError(err instanceof Error ? err.message : "The upload could not be analyzed.");
      }
      if (nextStatus?.access_restricted) window.dispatchEvent(new Event("cgs:account-refresh"));
      setBusy(false);
    }
  }

  return (
    <div className="upload-card">
      {!accessLoading && !isAuthenticated && !status?.can_analyze && !status?.access_restricted && (
        <div
          className="auth-prompt-card"
          role="alert"
          style={{
            marginBottom: "1.25rem",
            padding: "1rem 1.25rem",
            borderRadius: "10px",
            background: "rgba(239, 68, 68, 0.08)",
            border: "1px solid rgba(239, 68, 68, 0.28)",
            color: "var(--text)",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              fontWeight: 600,
              color: "var(--danger, #f87171)",
              marginBottom: "0.35rem",
              fontSize: "0.92rem",
            }}
          >
            <span aria-hidden="true">🔒</span> Authentication Strictly Required
          </div>
          <p style={{ margin: "0 0 0.85rem", fontSize: "0.85rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
            Unauthorized and unregistered users are strictly not permitted to start scanning or media inspection. Please log in to your verified account or sign up to begin.
          </p>
          <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
            <Link className="button button-primary btn-lime-themed" href="/login?next=/app/analyze" style={{ fontSize: "0.82rem", padding: "0.45rem 0.9rem" }}>
              Sign in to scan
            </Link>
            <Link className="button button-outline" href="/sign-up?next=/app/analyze" style={{ fontSize: "0.82rem", padding: "0.45rem 0.9rem" }}>
              Create free account
            </Link>
          </div>
        </div>
      )}

      {!inspectionsEnabled && (
        <div className="auth-lockout-notice" role="status">
          New inspections are temporarily paused by the platform administrator. Your existing reports remain available.
        </div>
      )}


      {/* Hidden file input */}
      <input
        ref={input}
        type="file"
        accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,video/quicktime,video/x-msvideo,audio/wav,audio/mpeg,audio/flac,audio/ogg,audio/mp4,audio/aac"
        onChange={onInput}
        className="visually-hidden"
        style={{ display: "none" }}
        disabled={!canAnalyze || busy}
        aria-label="Choose an image, video, or audio file"
      />

      <div
        className={`dropzone${dragging ? " dropzone-active" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => canAnalyze && input.current?.click()}
        role="button"
        aria-disabled={!canAnalyze}
        tabIndex={canAnalyze ? 0 : -1}
        onKeyDown={(e) => {
          if (!canAnalyze) return;
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            input.current?.click();
          }
        }}
      >
        <div className="upload-icon-wrapper" aria-hidden="true">
          <span className="upload-icon">
            {isVideo ? (
              <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="23 7 16 12 23 17 23 7" />
                <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
              </svg>
            ) : isAudio ? (
              <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 18V5l12-2v13" />
                <circle cx="6" cy="18" r="3" />
                <circle cx="18" cy="16" r="3" />
              </svg>
            ) : (
              <svg
                viewBox="0 0 24 24"
                width="28"
                height="28"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            )}
          </span>
        </div>

        <h3 className="dropzone-title">
          {file
            ? isVideo
              ? "Video file selected"
              : isAudio
                ? "Audio file selected"
                : "Image file selected"
            : "Drop an image, video, or audio file to inspect"}
        </h3>
        <p className="dropzone-sub">
          {file ? file.name : `Images, Videos, or Audio (WAV, MP3, FLAC, M4A, OGG) · up to ${maxLabel}`}
        </p>

        <button
          className="button button-outline button-choose-img"
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            if (canAnalyze) input.current?.click();
          }}
          disabled={!canAnalyze || busy}
        >
          {file ? "Replace media" : "Choose media file"}
        </button>
      </div>

      {file && (
        <div className="selected-file">
          {preview && (
            isVideo ? (
              <video
                src={preview}
                className="upload-thumb"
                muted
                playsInline
                autoPlay
                loop
              />
            ) : isAudio ? (
              <div className="upload-audio-preview" style={{ padding: "0.25rem 0.5rem" }}>
                <audio src={preview} controls style={{ maxHeight: "32px", width: "160px" }} />
              </div>
            ) : (
              <img className="upload-thumb" src={preview} alt={`Preview of ${file.name}`} />
            )
          )}
          <span className={`file-badge ${isVideo ? "file-badge-video" : isAudio ? "file-badge-audio" : ""}`}>
            {isVideo ? "VIDEO" : isAudio ? "AUDIO" : "IMG"}
          </span>
          <div className="file-details">
            <strong title={file.name}>{file.name}</strong>
            <small>
              {formatBytes(file.size)} · {file.type ? file.type.split("/")[1].toUpperCase() : (file.name.split(".").pop() || "FILE").toUpperCase()}
            </small>
          </div>
          <Tooltip label="Remove selected media">
            <button
              className="icon-button file-remove-btn"
              onClick={() => {
                setFile(null);
                setTypeVerification(null);
              }}
              aria-label="Remove selected media"
              type="button"
            >
              ×
            </button>
          </Tooltip>
        </div>
      )}

      {verifyingType && (
        <div className="type-verification-badge" style={{ background: "rgba(163, 230, 53, 0.08)", border: "1px dashed rgba(163, 230, 53, 0.4)" }}>
          <span className="spinner" style={{ width: 16, height: 16, marginRight: 8 }} />
          <span>Verifying binary container &amp; magic byte signatures…</span>
        </div>
      )}

      {typeVerification && typeVerification.verified && (
        <div className="type-verification-badge is-verified">
          <span className="type-verification-icon">✓</span>
          <div className="type-verification-details">
            <div className="type-verification-title">
              <strong>Type Verification: Passed</strong>
              <span className="type-pipeline-pill">
                {typeVerification.category.toUpperCase()} · {typeVerification.format}
              </span>
            </div>
            <p style={{ margin: "0.2rem 0", fontSize: "0.82rem", color: "var(--text-muted)" }}>
              {typeVerification.message}
            </p>
            <div className="type-verification-meta">
              <span>Magic Signature: <code>{typeVerification.magicHex || "N/A"}</code></span>
              <span style={{ marginLeft: "0.75rem" }}>
                Neural Pipeline: <strong>{typeVerification.modelPipeline}</strong>
              </span>
            </div>
          </div>
        </div>
      )}

      {busy && file && (
        <div style={{ margin: "1rem 0", borderRadius: "8px", overflow: "hidden" }}>
          <NeuralScanOverlay
            mediaType={typeVerification?.category || (isVideo ? "video" : isAudio ? "audio" : "image")}
            active={true}
            isPending={true}
            statusText="STREAMING ASSET TENSORS TO NEURAL MODEL"
            fileName={file.name}
          />
        </div>
      )}

      <div className="upload-consent">
        <span className="mini-shield" aria-hidden="true">
          <svg
            viewBox="0 0 24 24"
            width="14"
            height="14"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
        </span>
        <p>
          Media is stored privately in an ephemeral tenant-isolated vault. Delete it any time from your history. See
          our <a href="/privacy">privacy policy</a>.
        </p>
      </div>

      {error && (
        <p role="alert" className="form-error">
          <svg
            viewBox="0 0 24 24"
            width="16"
            height="16"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ marginRight: 6, flexShrink: 0 }}
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {error}
        </p>
      )}

      <button
        className="button button-primary button-wide btn-lime-themed"
        disabled={!file || busy || !canAnalyze}
        onClick={submit}
        type="button"
      >
        {busy ? (
          <>
            <span className="spinner" /> Analyzing media &amp; queueing forensics…
          </>
        ) : (
          <>
          {accessLoading
            ? "Checking access…"
            : status?.requires_email_verification
            ? "Verify your email to continue"
            : !inspectionsEnabled
            ? "Inspections temporarily paused"
            : !canAnalyze
            ? status?.access_restricted ? "Analysis unavailable" : "Access unavailable"
            : "Execute Neural Forensics Screening"} <span aria-hidden="true">→</span>
          </>
        )}
      </button>

      <p className="microcopy">
        Persistent neural worker online · AI screening status:{" "}
        <strong>{detectorStatus.replaceAll("_", " ")}</strong>. Frame continuity &amp; C2PA provenance are executed automatically.
      </p>
    </div>
  );
}
