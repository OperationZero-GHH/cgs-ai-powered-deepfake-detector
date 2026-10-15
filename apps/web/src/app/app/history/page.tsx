"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { api, formatDate, formatBytes, type Analysis } from "@/lib/api";
import { SmoothInput } from "@/components/smooth-input";

const PAGE_SIZE = 15;

export default function HistoryPage() {
  const [items, setItems] = useState<Analysis[]>([]);
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [busy, setBusy] = useState(true);
  const [deletingId, setDeletingId] = useState("");
  const [error, setError] = useState("");

  async function load(targetPage = page) {
    setBusy(true);
    try {
      const params = new URLSearchParams({ page: String(targetPage), page_size: String(PAGE_SIZE) });
      if (q) params.set("q", q);
      if (filter) params.set("status_filter", filter);
      if (fromDate) params.set("created_from", fromDate);
      if (toDate) params.set("created_to", toDate);
      const result = await api<{ items: Analysis[]; total: number }>(`/analyses?${params.toString()}`);
      setItems(result.items);
      setTotal(result.total);
      setPage(targetPage);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load history.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load(1);
  }, []);

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  async function remove(analysisId: string) {
    if (!window.confirm("Delete this forensic report and its stored image? This action is permanent and cannot be undone.")) return;
    setDeletingId(analysisId);
    setError("");
    try {
      await api<void>(`/analyses/${analysisId}`, { method: "DELETE" });
      const targetPage = items.length === 1 && page > 1 ? page - 1 : page;
      await load(targetPage);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete report.");
    } finally {
      setDeletingId("");
    }
  }

  function getBadgeClass(status: string, classification?: string) {
    if (status === "queued" || status === "processing") return "pill-pending";
    const cl = (classification || "").toLowerCase();
    if (cl.includes("synthetic") || cl.includes("ai_generated") || cl.includes("fake")) return "pill-suspicious";
    if (cl.includes("natural") || cl.includes("authentic") || cl.includes("real")) return "pill-authentic";
    return "pill-inconclusive";
  }

  return (
    <div className="dashboard-content history-page-content">
      {/* Top Banner */}
      <div className="dash-hero-banner history-hero-banner">
        <div className="dash-hero-info">
          <div className="dash-hero-eyebrow">
            <span className="live-dot-pulse" aria-hidden="true" />
            <span>IMMUTABLE EVIDENCE LEDGER · RETENTION VAULT</span>
          </div>
          <h1>Inspection History Ledger</h1>
          <p>
            Audit, search, and manage verified image inspection records. Every entry is indexed with its cryptographic SHA-256 fingerprint and forensic metadata.
          </p>
        </div>
        <div className="dash-hero-actions">
          <Link className="button button-primary btn-lime-themed" href="/app/analyze">
            <span>+ New inspection</span>
            <span className="arrow" aria-hidden="true">→</span>
          </Link>
        </div>
      </div>

      {/* Main Panel */}
      <section className="dash-panel history-panel">
        <div className="history-toolbar">
          <div className="history-search-wrap">
            <SmoothInput
              value={q}
              onChange={(event) => setQ(event.target.value)}
              placeholder="Search by case ID or filename…"
              aria-label="Search by case ID or filename"
            />
          </div>

          <div className="history-filters-row">
            <select
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
              aria-label="Filter by inspection status"
              className="history-select"
            >
              <option value="">All statuses</option>
              <option value="completed">Completed</option>
              <option value="queued">Queued</option>
              <option value="processing">Processing</option>
              <option value="failed">Failed</option>
            </select>

            <div className="date-picker-cluster">
              <label className="date-filter-label">
                <span>From</span>
                <input
                  type="date"
                  value={fromDate}
                  onChange={(event) => setFromDate(event.target.value)}
                  aria-label="Created from date"
                  className="history-date-input"
                />
              </label>

              <label className="date-filter-label">
                <span>To</span>
                <input
                  type="date"
                  value={toDate}
                  onChange={(event) => setToDate(event.target.value)}
                  aria-label="Created to date"
                  className="history-date-input"
                />
              </label>
            </div>

            <button
              className="button button-primary btn-lime-themed history-filter-btn"
              onClick={() => void load(1)}
              type="button"
            >
              Filter Ledger
            </button>
          </div>
        </div>

        {error && (
          <div className="dash-error-state" role="alert">
            <span className="alert-icon">!</span>
            <div>
              <strong>Ledger query error</strong>
              <p>{error}</p>
            </div>
          </div>
        )}

        {busy ? (
          <div className="dash-skeleton-list">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="dash-skeleton-row" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="dash-empty-state">
            <div className="empty-icon" aria-hidden="true">📂</div>
            <h3>No matching inspection records</h3>
            <p>Try clearing filters or launch a new image screening in the studio.</p>
            <Link className="button button-primary btn-lime-themed" href="/app/analyze">
              Start new inspection
            </Link>
          </div>
        ) : (
          <div className="dash-table-container">
            <table className="dash-reports-table">
              <thead>
                <tr>
                  <th>EVIDENCE ID</th>
                  <th>TIMESTAMP</th>
                  <th>FILE ATTRIBUTES</th>
                  <th>CLASSIFICATION</th>
                  <th>MANAGEMENT</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, index) => (
                  <motion.tr
                    key={item.analysis_id}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2, delay: index * 0.03 }}
                  >
                    <td className="id-cell">
                      <Link href={`/app/analyses/${item.analysis_id}`} className="evidence-link">
                        <code>{item.analysis_id.slice(0, 12).toUpperCase()}</code>
                      </Link>
                    </td>
                    <td className="date-cell">
                      {formatDate(item.created_at)}
                    </td>
                    <td className="file-cell">
                      <span className="file-thumb-pill" aria-hidden="true">
                        {item.file.detected_mime_type?.split("/")[1]?.toUpperCase() || "IMG"}
                      </span>
                      <div className="file-meta">
                        <Link href={`/app/analyses/${item.analysis_id}`} className="file-name" title={item.file.original_filename}>
                          {item.file.original_filename}
                        </Link>
                        <span className="file-sub">
                          {formatBytes(item.file.size_bytes)} · {item.file.detected_mime_type}
                        </span>
                      </div>
                    </td>
                    <td className="status-cell">
                      <span className={`dash-result-pill ${getBadgeClass(item.status, item.summary?.classification)}`}>
                        {item.status === "queued" || item.status === "processing"
                          ? item.status.toUpperCase()
                          : item.summary?.classification?.replaceAll("_", " ").toUpperCase() || "RECORDED"}
                      </span>
                    </td>
                    <td className="action-cell">
                      <div className="history-action-cluster">
                        <Link href={`/app/analyses/${item.analysis_id}`} className="row-action-btn" aria-label={`Open report ${item.analysis_id}`}>
                          View <span>→</span>
                        </Link>
                        <button
                          className="history-delete-btn"
                          onClick={() => void remove(item.analysis_id)}
                          disabled={deletingId === item.analysis_id}
                          aria-label={`Delete report ${item.analysis_id}`}
                          title="Permanently purge this record"
                        >
                          {deletingId === item.analysis_id ? "Purging…" : "Purge"}
                        </button>
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="history-pagination-bar">
          <small className="pagination-info">
            Showing {items.length} of {total} record{total === 1 ? "" : "s"} · Page {page} of {pageCount}
          </small>
          <div className="pagination-buttons">
            <button
              className="button button-outline button-small"
              disabled={busy || page <= 1}
              onClick={() => void load(page - 1)}
            >
              Previous
            </button>
            <button
              className="button button-outline button-small"
              disabled={busy || page >= pageCount}
              onClick={() => void load(page + 1)}
            >
              Next
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
