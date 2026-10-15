"use client";

import { useState, type FormEvent } from "react";
import { api, ApiError } from "@/lib/api";
import { SmoothInput } from "@/components/smooth-input";

export function ContactForm() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [topic, setTopic] = useState("product");
  const [message, setMessage] = useState("");
  const [website, setWebsite] = useState("");
  const [busy, setBusy] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setErrorMessage("");
    setSuccessMessage("");

    if (!name.trim()) {
      setErrorMessage("Please enter your name.");
      return;
    }
    if (!email.trim() || !email.includes("@")) {
      setErrorMessage("Please enter a valid email address.");
      return;
    }
    if (message.trim().length < 10) {
      setErrorMessage("Please enter a message of at least 10 characters.");
      return;
    }

    setBusy(true);

    try {
      const response = await api<{ submitted: boolean; message: string }>("/support/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          topic,
          message: message.trim(),
          website,
        }),
      });

      setSuccessMessage(
        response.message || "Thank you for reaching out! Your inquiry has been received and our team will get back to you shortly."
      );
      setName("");
      setEmail("");
      setTopic("product");
      setMessage("");
      setWebsite("");
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message || "Could not submit inquiry. Please try again.");
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("An unexpected network error occurred. Please try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  function resetForm() {
    setSuccessMessage("");
    setErrorMessage("");
  }

  if (successMessage) {
    return (
      <div
        className="contact-success-card"
        role="status"
        style={{
          padding: "2rem 1.5rem",
          borderRadius: "14px",
          background: "rgba(34, 197, 94, 0.08)",
          border: "1px solid rgba(34, 197, 94, 0.3)",
          textAlign: "center",
          animation: "fadeIn 0.3s ease-out",
        }}
      >
        <div
          style={{
            width: "52px",
            height: "52px",
            borderRadius: "50%",
            background: "rgba(34, 197, 94, 0.2)",
            color: "#22c55e",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "1.75rem",
            marginBottom: "1rem",
          }}
          aria-hidden="true"
        >
          ✓
        </div>
        <h3 style={{ fontSize: "1.25rem", margin: "0 0 0.5rem", color: "var(--text)" }}>
          Inquiry Successfully Dispatched
        </h3>
        <p style={{ margin: "0 auto 1.5rem", maxWidth: "480px", color: "var(--text-muted)", fontSize: "0.92rem", lineHeight: 1.6 }}>
          {successMessage}
        </p>
        <button
          type="button"
          className="button button-outline"
          onClick={resetForm}
          style={{ fontSize: "0.85rem", padding: "0.5rem 1.25rem" }}
        >
          Send another message
        </button>
      </div>
    );
  }

  return (
    <form className="contact-form" onSubmit={submit} noValidate>
      {/* Honeypot field for bot spam detection */}
      <div style={{ display: "none" }} aria-hidden="true">
        <label htmlFor="contact-website">Website</label>
        <input
          id="contact-website"
          name="website"
          value={website}
          onChange={(e) => setWebsite(e.target.value)}
          tabIndex={-1}
          autoComplete="off"
        />
      </div>

      <div className="contact-field">
        <label htmlFor="contact-name">
          Name <span style={{ color: "var(--danger, #f87171)" }}>*</span>
        </label>
        <SmoothInput
          id="contact-name"
          name="name"
          autoComplete="name"
          maxLength={80}
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Jane Doe"
          required
        />
      </div>

      <div className="contact-field">
        <label htmlFor="contact-email">
          Work or Contact Email <span style={{ color: "var(--danger, #f87171)" }}>*</span>
        </label>
        <SmoothInput
          id="contact-email"
          name="email"
          type="email"
          autoComplete="email"
          maxLength={320}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="jane@company.com"
          required
        />
      </div>

      <div className="contact-field contact-field-wide">
        <label htmlFor="contact-topic">Inquiry Category</label>
        <select
          id="contact-topic"
          name="topic"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
        >
          <option value="product">Product Information &amp; Architecture</option>
          <option value="technical">Technical Support &amp; AI Forensics Pipeline</option>
          <option value="privacy">Privacy, Security &amp; C2PA Cryptographic Provenance</option>
          <option value="enterprise">Enterprise Licensing &amp; Dedicated Deployment</option>
          <option value="other">General Feedback &amp; Other Inquiries</option>
        </select>
      </div>

      <div className="contact-field contact-field-wide">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "0.25rem" }}>
          <label htmlFor="contact-message" style={{ margin: 0 }}>
            Message <span style={{ color: "var(--danger, #f87171)" }}>*</span>
          </label>
          <small style={{ color: "var(--text-faint)", fontSize: "0.75rem" }}>
            {message.length} / 3000
          </small>
        </div>
        <textarea
          id="contact-message"
          name="message"
          rows={5}
          minLength={10}
          maxLength={3000}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Provide details about your query or incident evaluation..."
          required
        />
        <small style={{ color: "var(--text-faint)", fontSize: "0.75rem", marginTop: "0.25rem", display: "block" }}>
          Inquiries are encrypted and reviewed under strict confidentiality guidelines.
        </small>
      </div>

      {errorMessage && (
        <div
          role="alert"
          style={{
            gridColumn: "1 / -1",
            padding: "0.75rem 1rem",
            borderRadius: "8px",
            background: "rgba(239, 68, 68, 0.1)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            color: "var(--danger, #f87171)",
            fontSize: "0.85rem",
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
          }}
        >
          <span aria-hidden="true">⚠️</span>
          <span>{errorMessage}</span>
        </div>
      )}

      <button
        className="button button-primary btn-lime-themed"
        type="submit"
        disabled={busy}
        style={{ minWidth: "180px" }}
      >
        {busy ? (
          <>
            <span className="spinner" style={{ marginRight: "0.5rem" }} /> Sending inquiry…
          </>
        ) : (
          <>
            Send inquiry <span aria-hidden="true">→</span>
          </>
        )}
      </button>

      <p className="contact-form__status" role="status">
        Response SLA: within 15–60 minutes for high-priority forensics inquiries.
      </p>
    </form>
  );
}
