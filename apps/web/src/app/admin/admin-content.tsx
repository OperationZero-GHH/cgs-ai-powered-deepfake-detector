"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, formatBytes, formatDate } from "@/lib/api";

type Overview = {
  analysis_counts: Record<string, number>;
  queue_counts: Record<string, number>;
  active_users: number;
  total_users: number;
  detector: { status: string; model_id: string | null; model_version: string | null; details: string };
  worker: { status: string; active_workers: number };
  note: string;
};

type AdminUser = {
  id: string;
  email: string;
  display_name: string;
  username: string | null;
  phone_number: string | null;
  role: string;
  active: boolean;
  signup_method: string;
  signup_ip: string | null;
  email_verified: boolean;
  created_at: string;
  analysis_count: number;
};

type QueueJob = {
  id: string;
  analysis_id: string;
  status: string;
  attempts: number;
  worker_id: string | null;
  last_error: string | null;
  created_at: string;
};

type AuditEvent = {
  id: string;
  actor_id: string | null;
  actor_email: string | null;
  actor_name: string | null;
  action: string;
  subject_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
};

type UserActivityEvent = AuditEvent;
type AdminAccount = { id: string; email: string; display_name: string; username: string | null; phone_number: string | null; active: boolean; email_verified: boolean; created_at: string; protected: boolean };
type AdminInvitation = { id: string; email: string; created_at: string; expires_at: string };
type AdminInvitationResult = { invited?: boolean; promoted?: boolean; email: string; email_sent?: boolean; invite_url?: string | null };
type TrafficSummary = { window_hours: number; access_events_24h: number; inspections_24h: number; signups_24h: number; active_rate_limit_buckets: number; expired_rate_limit_buckets: number; blocked_networks: number; allowlisted_networks: number; event_breakdown: Array<{ action: string; count: number }> };
type AllowlistedNetwork = { ip_hash: string; fingerprint: string; reason: string; created_at: string };

type AdminAnalysis = {
  analysis_id: string;
  status: string;
  created_at: string;
  completed_at: string | null;
  file: { original_filename: string; detected_mime_type: string; size_bytes: number; width: number; height: number; sha256: string };
  summary: { classification: string; confidence_value: number | null; explanation: string };
  owner_email: string | null;
  owner_name: string | null;
};

type ContactInquiry = {
  id: string;
  name: string;
  email: string;
  topic: string;
  message: string;
  status: "new" | "in_progress" | "resolved";
  admin_note: string | null;
  created_at: string;
  updated_at: string;
};

type AdminSettings = { registration_enabled: boolean; inspections_enabled: boolean };
type IpBlock = { id: string; reference_id: string; status: string; reason: string; linked_accounts: Array<{ email: string }>; created_at: string; raised_limit: number | null };
type UnblockRequest = { id: string; reference_id: string; name: string; email: string; reason: string; status: string; created_at: string };

const PAGE_SIZE = 50;

function statusClass(status: string) {
  if (["active", "completed", "resolved", "ready", "unblocked", "whitelisted"].includes(status)) return "is-good";
  if (["failed", "disabled", "blocked", "rejected"].includes(status)) return "is-bad";
  if (["processing", "in_progress"].includes(status)) return "is-running";
  return "is-neutral";
}

function Metric({ label, value, detail }: { label: string; value: string | number; detail: string }) {
  return (
    <article className="admin-metric-card">
      <span className="admin-eyebrow">{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function SearchField({ value, onChange, placeholder, label }: { value: string; onChange: (value: string) => void; placeholder: string; label: string }) {
  return (
    <label className="admin-search-field">
      <span className="admin-search-icon" aria-hidden="true">⌕</span>
      <input aria-label={label} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />
    </label>
  );
}

export default function AdminContent() {
  const [activeSection, setActiveSection] = useState("overview");
  const [data, setData] = useState<Overview | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [userTotal, setUserTotal] = useState(0);
  const [userPage, setUserPage] = useState(1);
  const [jobs, setJobs] = useState<QueueJob[]>([]);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [auditTotal, setAuditTotal] = useState(0);
  const [auditPage, setAuditPage] = useState(1);
  const [userLogs, setUserLogs] = useState<UserActivityEvent[]>([]);
  const [userLogTotal, setUserLogTotal] = useState(0);
  const [userLogPage, setUserLogPage] = useState(1);
  const [adminAccounts, setAdminAccounts] = useState<AdminAccount[]>([]);
  const [adminInvitations, setAdminInvitations] = useState<AdminInvitation[]>([]);
  const [traffic, setTraffic] = useState<TrafficSummary | null>(null);
  const [allowlistedNetworks, setAllowlistedNetworks] = useState<AllowlistedNetwork[]>([]);
  const [analyses, setAnalyses] = useState<AdminAnalysis[]>([]);
  const [analysisTotal, setAnalysisTotal] = useState(0);
  const [ledgerPage, setLedgerPage] = useState(1);
  const [inquiries, setInquiries] = useState<ContactInquiry[]>([]);
  const [contactTotal, setContactTotal] = useState(0);
  const [contactPage, setContactPage] = useState(1);
  const [settings, setSettings] = useState<AdminSettings>({ registration_enabled: true, inspections_enabled: true });
  const [ipBlocks, setIpBlocks] = useState<IpBlock[]>([]);
  const [unblockRequests, setUnblockRequests] = useState<UnblockRequest[]>([]);
  const [ledgerQuery, setLedgerQuery] = useState("");
  const [ledgerStatus, setLedgerStatus] = useState("");
  const [userQuery, setUserQuery] = useState("");
  const [adminQuery, setAdminQuery] = useState("");
  const [adminInviteEmail, setAdminInviteEmail] = useState("");
  const [adminInviteUrl, setAdminInviteUrl] = useState("");
  const [userLogQuery, setUserLogQuery] = useState("");
  const [adminLogQuery, setAdminLogQuery] = useState("");
  const [userLogConfirmation, setUserLogConfirmation] = useState("");
  const [adminLogConfirmation, setAdminLogConfirmation] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<AdminUser | null>(null);
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [adminActionTarget, setAdminActionTarget] = useState<AdminAccount | null>(null);
  const [adminActionConfirmation, setAdminActionConfirmation] = useState("");
  const [securityIp, setSecurityIp] = useState("");
  const [securityIpReason, setSecurityIpReason] = useState("");
  const [trafficIp, setTrafficIp] = useState("");
  const [trafficIpReason, setTrafficIpReason] = useState("");
  const [trafficCleanupConfirmation, setTrafficCleanupConfirmation] = useState("");
  const [contactQuery, setContactQuery] = useState("");
  const [contactStatus, setContactStatus] = useState("");
  const [noteDrafts, setNoteDrafts] = useState<Record<string, string>>({});
  const [settingsConfirmation, setSettingsConfirmation] = useState("");
  const [dangerConfirmation, setDangerConfirmation] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(true);
  const [busyId, setBusyId] = useState("");
  const [lastRefreshed, setLastRefreshed] = useState("");

  const refresh = useCallback(async () => {
    setBusy(true);
    try {
      const [overview, userResult, queueResult, auditResult, userLogResult, adminResult, trafficResult, whitelistResult, ledger, contactResult, settingResult, blockResult, requestResult] = await Promise.all([
        api<Overview>("/admin/overview"),
        api<{ items: AdminUser[]; total: number }>(`/admin/users?page=1&page_size=${PAGE_SIZE}`),
        api<{ items: QueueJob[] }>(`/admin/queue?page_size=${PAGE_SIZE}`),
        api<{ items: AuditEvent[]; total: number }>(`/admin/audit?page=1&page_size=${PAGE_SIZE}`),
        api<{ items: UserActivityEvent[]; total: number }>(`/admin/user-logs?page=1&page_size=${PAGE_SIZE}`),
        api<{ items: AdminAccount[]; invitations: AdminInvitation[] }>("/admin/admins"),
        api<TrafficSummary>("/admin/traffic"),
        api<{ items: AllowlistedNetwork[] }>("/admin/ip-whitelist"),
        api<{ items: AdminAnalysis[]; total: number }>(`/admin/analyses?page=1&page_size=${PAGE_SIZE}`),
        api<{ items: ContactInquiry[]; total: number }>(`/admin/contact-inquiries?page=1&page_size=${PAGE_SIZE}`),
        api<{ settings: AdminSettings }>("/admin/settings"),
        api<{ items: IpBlock[] }>("/admin/ip-blocks?limit=100"),
        api<{ items: UnblockRequest[] }>("/admin/unblock-requests?status_filter=pending&limit=100"),
      ]);
      setData(overview);
      setUsers(userResult.items);
      setUserTotal(userResult.total);
      setUserPage(1);
      setJobs(queueResult.items);
      setAudit(auditResult.items);
      setAuditTotal(auditResult.total);
      setAuditPage(1);
      setUserLogs(userLogResult.items);
      setUserLogTotal(userLogResult.total);
      setUserLogPage(1);
      setAdminAccounts(adminResult.items);
      setAdminInvitations(adminResult.invitations);
      setTraffic(trafficResult);
      setAllowlistedNetworks(whitelistResult.items);
      setAnalyses(ledger.items);
      setAnalysisTotal(ledger.total);
      setLedgerPage(1);
      setInquiries(contactResult.items);
      setContactTotal(contactResult.total);
      setContactPage(1);
      setSettings(settingResult.settings);
      setIpBlocks(blockResult.items);
      setUnblockRequests(requestResult.items);
      setError("");
      setLastRefreshed(new Date().toLocaleTimeString());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load administrator data.");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  useEffect(() => {
    const sections = new Set(["overview", "ledger", "users", "control", "contacts", "admins", "user-logs", "admin-logs", "security", "traffic", "settings"]);
    const syncSection = () => {
      const requested = decodeURIComponent(window.location.hash.slice(1));
      setActiveSection(sections.has(requested) ? requested : "overview");
    };
    const syncSelectedSection = (event: Event) => {
      const requested = (event as CustomEvent<unknown>).detail;
      if (typeof requested === "string" && sections.has(requested)) setActiveSection(requested);
    };
    syncSection();
    window.addEventListener("hashchange", syncSection);
    window.addEventListener("cgs:admin-section-change", syncSelectedSection);
    return () => {
      window.removeEventListener("hashchange", syncSection);
      window.removeEventListener("cgs:admin-section-change", syncSelectedSection);
    };
  }, []);

  useEffect(() => {
    window.requestAnimationFrame(() => document.getElementById(activeSection)?.scrollIntoView({ behavior: "auto", block: "start" }));
  }, [activeSection]);

  async function searchLedger(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      const params = new URLSearchParams({ page: "1", page_size: String(PAGE_SIZE) });
      if (ledgerQuery.trim()) params.set("q", ledgerQuery.trim());
      if (ledgerStatus) params.set("status_filter", ledgerStatus);
      const result = await api<{ items: AdminAnalysis[]; total: number }>(`/admin/analyses?${params}`);
      setAnalyses(result.items);
      setAnalysisTotal(result.total);
      setLedgerPage(1);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to search inspections.");
    } finally { setBusy(false); }
  }

  async function changeLedgerPage(targetPage: number) {
    setBusy(true);
    try {
      const params = new URLSearchParams({ page: String(targetPage), page_size: String(PAGE_SIZE) });
      if (ledgerQuery.trim()) params.set("q", ledgerQuery.trim());
      if (ledgerStatus) params.set("status_filter", ledgerStatus);
      const result = await api<{ items: AdminAnalysis[]; total: number }>(`/admin/analyses?${params}`);
      setAnalyses(result.items);
      setAnalysisTotal(result.total);
      setLedgerPage(targetPage);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load inspection records.");
    } finally { setBusy(false); }
  }

  async function searchUsers(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      const params = new URLSearchParams({ page: "1", page_size: String(PAGE_SIZE) });
      if (userQuery.trim()) params.set("q", userQuery.trim());
      const result = await api<{ items: AdminUser[]; total: number }>(`/admin/users?${params}`);
      setUsers(result.items);
      setUserTotal(result.total);
      setUserPage(1);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to search accounts.");
    } finally { setBusy(false); }
  }

  async function changeUserPage(targetPage: number) {
    setBusy(true);
    try {
      const params = new URLSearchParams({ page: String(targetPage), page_size: String(PAGE_SIZE) });
      if (userQuery.trim()) params.set("q", userQuery.trim());
      const result = await api<{ items: AdminUser[]; total: number }>(`/admin/users?${params}`);
      setUsers(result.items);
      setUserTotal(result.total);
      setUserPage(targetPage);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load user records.");
    } finally { setBusy(false); }
  }

  async function searchAdminAccounts(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      const params = new URLSearchParams();
      if (adminQuery.trim()) params.set("q", adminQuery.trim());
      const result = await api<{ items: AdminAccount[]; invitations: AdminInvitation[] }>(`/admin/admins?${params}`);
      setAdminAccounts(result.items);
      setAdminInvitations(result.invitations);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to search administrator accounts.");
    } finally { setBusy(false); }
  }

  async function inviteAdmin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusyId("admin-invite");
    setAdminInviteUrl("");
    setError("");
    setNotice("");
    try {
      const result = await api<AdminInvitationResult>("/admin/admins", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: adminInviteEmail.trim() }),
      });
      setAdminInviteEmail("");
      setAdminInviteUrl(result.invite_url || "");
      setNotice(result.promoted
        ? `${result.email} now has administrator access.`
        : result.email_sent === false
          ? `The invitation for ${result.email} was created, but email delivery is unavailable. Copy the one-time setup link below and share it securely.`
          : `Administrator invitation sent to ${result.email}.`);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to create this administrator invitation.");
    } finally { setBusyId(""); }
  }

  async function copyAdminInviteUrl() {
    if (!adminInviteUrl) return;
    try {
      await navigator.clipboard.writeText(adminInviteUrl);
      setNotice("Administrator setup link copied.");
    } catch {
      setNotice("Copy was blocked by the browser. Select the setup link below and copy it manually.");
    }
  }

  async function cancelAdminInvitation(invitation: AdminInvitation) {
    setBusyId(invitation.id);
    setError("");
    try {
      await api(`/admin/admin-invitations/${invitation.id}`, { method: "DELETE" });
      setAdminInviteUrl("");
      setNotice(`Invitation for ${invitation.email} canceled.`);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to cancel this invitation.");
    } finally { setBusyId(""); }
  }

  async function updateAdmin(account: AdminAccount, action: "disable" | "restore" | "revoke") {
    if (action === "revoke" && adminActionConfirmation !== `REVOKE ADMIN ${account.email}`) {
      setError(`Type REVOKE ADMIN ${account.email} to remove this administrator role.`);
      return;
    }
    setBusyId(account.id);
    setError("");
    try {
      await api(`/admin/admins/${account.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action }) });
      setAdminActionTarget(null);
      setAdminActionConfirmation("");
      setNotice(action === "revoke" ? `Administrator access removed for ${account.email}.` : `Administrator account ${action === "disable" ? "disabled" : "restored"}.`);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to update this administrator.");
    } finally { setBusyId(""); }
  }

  async function searchUserLogs(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      const params = new URLSearchParams({ page: "1", page_size: String(PAGE_SIZE) });
      if (userLogQuery.trim()) params.set("q", userLogQuery.trim());
      const result = await api<{ items: UserActivityEvent[]; total: number }>(`/admin/user-logs?${params}`);
      setUserLogs(result.items);
      setUserLogTotal(result.total);
      setUserLogPage(1);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to search user activity logs.");
    } finally { setBusy(false); }
  }

  async function changeUserLogPage(targetPage: number) {
    setBusy(true);
    try {
      const params = new URLSearchParams({ page: String(targetPage), page_size: String(PAGE_SIZE) });
      if (userLogQuery.trim()) params.set("q", userLogQuery.trim());
      const result = await api<{ items: UserActivityEvent[]; total: number }>(`/admin/user-logs?${params}`);
      setUserLogs(result.items);
      setUserLogTotal(result.total);
      setUserLogPage(targetPage);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load user activity logs.");
    } finally { setBusy(false); }
  }

  async function searchAdminLogs(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      const params = new URLSearchParams({ page: "1", page_size: String(PAGE_SIZE) });
      if (adminLogQuery.trim()) params.set("q", adminLogQuery.trim());
      const result = await api<{ items: AuditEvent[]; total: number }>(`/admin/audit?${params}`);
      setAudit(result.items);
      setAuditTotal(result.total);
      setAuditPage(1);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to search administrator logs.");
    } finally { setBusy(false); }
  }

  async function changeAdminLogPage(targetPage: number) {
    setBusy(true);
    try {
      const params = new URLSearchParams({ page: String(targetPage), page_size: String(PAGE_SIZE) });
      if (adminLogQuery.trim()) params.set("q", adminLogQuery.trim());
      const result = await api<{ items: AuditEvent[]; total: number }>(`/admin/audit?${params}`);
      setAudit(result.items);
      setAuditTotal(result.total);
      setAuditPage(targetPage);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load administrator logs.");
    } finally { setBusy(false); }
  }

  async function searchContacts(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      const params = new URLSearchParams({ page: "1", page_size: String(PAGE_SIZE) });
      if (contactQuery.trim()) params.set("q", contactQuery.trim());
      if (contactStatus) params.set("status_filter", contactStatus);
      const result = await api<{ items: ContactInquiry[]; total: number }>(`/admin/contact-inquiries?${params}`);
      setInquiries(result.items);
      setContactTotal(result.total);
      setContactPage(1);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to search contact inquiries.");
    } finally { setBusy(false); }
  }

  async function changeContactPage(targetPage: number) {
    setBusy(true);
    try {
      const params = new URLSearchParams({ page: String(targetPage), page_size: String(PAGE_SIZE) });
      if (contactQuery.trim()) params.set("q", contactQuery.trim());
      if (contactStatus) params.set("status_filter", contactStatus);
      const result = await api<{ items: ContactInquiry[]; total: number }>(`/admin/contact-inquiries?${params}`);
      setInquiries(result.items);
      setContactTotal(result.total);
      setContactPage(targetPage);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load contact inquiries.");
    } finally { setBusy(false); }
  }

  async function updateUser(user: AdminUser, active: boolean) {
    setBusyId(user.id);
    setError("");
    try {
      await api(`/admin/users/${user.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ active }) });
      setNotice(active ? `${user.email} can sign in again.` : `${user.email} has been banned and signed out.`);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to update this account.");
    } finally { setBusyId(""); }
  }

  async function deleteUser() {
    if (!deleteTarget) return;
    const expected = `DELETE USER ${deleteTarget.email}`;
    if (deleteConfirmation !== expected) {
      setError(`Type ${expected} exactly to delete this account.`);
      return;
    }
    setBusyId(deleteTarget.id);
    setError("");
    try {
      const result = await api<{ inspections_deleted: number }>(`/admin/users/${deleteTarget.id}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmation: deleteConfirmation }),
      });
      setNotice(`Account deleted with ${result.inspections_deleted} inspection record(s) and their stored media.`);
      setDeleteTarget(null);
      setDeleteConfirmation("");
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to delete this account.");
    } finally { setBusyId(""); }
  }

  async function clearLogs(which: "user" | "admin") {
    const expected = which === "user" ? "DELETE ALL USER LOGS" : "DELETE ALL ADMIN LOGS";
    const confirmation = which === "user" ? userLogConfirmation : adminLogConfirmation;
    if (confirmation !== expected) {
      setError(`Type ${expected} exactly to continue.`);
      return;
    }
    setBusyId(`${which}-logs-clear`);
    setError("");
    try {
      const endpoint = which === "user" ? "/admin/user-logs" : "/admin/audit";
      const result = await api<{ deleted_entries: number }>(endpoint, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmation }),
      });
      if (which === "user") setUserLogConfirmation("");
      else setAdminLogConfirmation("");
      setNotice(`${result.deleted_entries} ${which} log entr${result.deleted_entries === 1 ? "y" : "ies"} removed. The purge is recorded in the opposite audit trail.`);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : `Unable to clear ${which} logs.`);
    } finally { setBusyId(""); }
  }

  async function blockNetwork(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusyId("security-block-ip");
    setError("");
    try {
      const result = await api<{ reference_id: string }>("/admin/security/block-ip", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ip_address: securityIp.trim(), reason: securityIpReason.trim() || "Administrator network restriction" }),
      });
      setSecurityIp("");
      setSecurityIpReason("");
      setNotice(`Network restriction ${result.reference_id} is active.`);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to restrict this network.");
    } finally { setBusyId(""); }
  }

  async function allowNetwork(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusyId("traffic-allow-ip");
    setError("");
    try {
      await api("/admin/ip-whitelist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ip_address: trafficIp.trim(), reason: trafficIpReason.trim() }),
      });
      setTrafficIp("");
      setTrafficIpReason("");
      setNotice("Network allowlist updated.");
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to allow this network.");
    } finally { setBusyId(""); }
  }

  async function removeAllowedNetwork(entry: AllowlistedNetwork) {
    setBusyId(entry.ip_hash);
    setError("");
    try {
      await api(`/admin/ip-whitelist/${entry.ip_hash}`, { method: "DELETE" });
      setNotice(`Allowlist entry ${entry.fingerprint} removed.`);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to remove this network.");
    } finally { setBusyId(""); }
  }

  async function clearExpiredTraffic() {
    setBusyId("traffic-cleanup");
    setError("");
    try {
      const result = await api<{ deleted_entries: number }>("/admin/traffic/clear-expired", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmation: trafficCleanupConfirmation }),
      });
      setTrafficCleanupConfirmation("");
      setNotice(`${result.deleted_entries} expired rate-limit counter(s) cleared.`);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to clear expired counters.");
    } finally { setBusyId(""); }
  }

  async function retryJob(job: QueueJob) {
    setBusyId(job.id);
    setError("");
    try {
      await api(`/admin/analyses/${job.analysis_id}/retry`, { method: "POST" });
      setNotice(`Inspection ${job.analysis_id.slice(0, 12).toUpperCase()} was added to the processing queue.`);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to queue this report again.");
    } finally { setBusyId(""); }
  }

  async function updateInquiry(inquiry: ContactInquiry, patch: { status?: ContactInquiry["status"]; admin_note?: string }) {
    setBusyId(inquiry.id);
    setError("");
    try {
      await api(`/admin/contact-inquiries/${inquiry.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(patch) });
      setNotice("Inquiry updated.");
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to update this inquiry.");
    } finally { setBusyId(""); }
  }

  async function saveSettings() {
    setBusyId("settings");
    setError("");
    setNotice("");
    try {
      await api("/admin/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...settings, confirmation: settingsConfirmation }),
      });
      setSettingsConfirmation("");
      setNotice("Platform settings saved and enforced by the API.");
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to save platform settings.");
    } finally { setBusyId(""); }
  }

  async function revokeOtherSessions() {
    setBusyId("revoke-sessions");
    setError("");
    setNotice("");
    try {
      const result = await api<{ revoked_sessions: number }>("/admin/security/revoke-other-sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmation: dangerConfirmation }),
      });
      setDangerConfirmation("");
      setNotice(`${result.revoked_sessions} other administrator session${result.revoked_sessions === 1 ? "" : "s"} revoked.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to revoke the other sessions.");
    } finally { setBusyId(""); }
  }

  async function unblockIp(block: IpBlock) {
    setBusyId(block.id);
    setError("");
    try {
      await api(`/admin/ip-blocks/${block.id}/unblock`, { method: "POST" });
      setNotice(`${block.reference_id} has been unblocked.`);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to unblock this network.");
    } finally { setBusyId(""); }
  }

  async function resolveRequest(request: UnblockRequest, status: "approved" | "rejected") {
    setBusyId(request.id);
    setError("");
    try {
      await api(`/admin/unblock-requests/${request.id}/resolve`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status, note: "Reviewed in the administrator console." }) });
      setNotice(`Access request ${status}.`);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to resolve this access request.");
    } finally { setBusyId(""); }
  }

  const queued = (data?.queue_counts.queued ?? 0) + (data?.queue_counts.processing ?? 0);
  const pendingContacts = inquiries.filter((item) => item.status === "new").length;
  const ledgerPageCount = Math.max(1, Math.ceil(analysisTotal / PAGE_SIZE));
  const userPageCount = Math.max(1, Math.ceil(userTotal / PAGE_SIZE));
  const contactPageCount = Math.max(1, Math.ceil(contactTotal / PAGE_SIZE));
  const userLogPageCount = Math.max(1, Math.ceil(userLogTotal / PAGE_SIZE));
  const auditPageCount = Math.max(1, Math.ceil(auditTotal / PAGE_SIZE));

  return (
    <div className="dashboard-content admin-console">
      <header className="admin-console-header" id="overview" hidden={activeSection !== "overview"}>
        <div>
          <span className="admin-eyebrow"><span className="admin-status-orb" /> ADMINISTRATION · SECURE OPERATIONS</span>
          <h1>Operations overview</h1>
          <p>Review platform health, manage inspection records, and respond to user support requests.</p>
        </div>
      </header>

      <div className="admin-console-tools">
        {lastRefreshed && <span className="admin-muted">Updated {lastRefreshed}</span>}
        <button className="button button-outline" type="button" onClick={() => void refresh()} disabled={busy}>
          <span aria-hidden="true">↻</span> {busy ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {error && <div className="admin-alert admin-alert--error" role="alert"><strong>Action needs attention</strong><span>{error}</span></div>}
      {notice && <div className="admin-alert admin-alert--success" role="status"><strong>Complete</strong><span>{notice}</span><button type="button" aria-label="Dismiss notification" onClick={() => setNotice("")}>×</button></div>}

      {!data && busy ? (
        <div className="admin-loading-card"><span className="auth-loading-spinner" aria-hidden="true" /><span>Loading secure platform data…</span></div>
      ) : (
        <>
          <section className="admin-metric-grid" aria-label="Platform summary" hidden={activeSection !== "overview"}>
            <Metric label="Active accounts" value={`${data?.active_users ?? 0} / ${data?.total_users ?? 0}`} detail="Currently enabled accounts" />
            <Metric label="Inspections" value={data?.analysis_counts.completed ?? 0} detail={`${data?.analysis_counts.failed ?? 0} failed · ${data?.analysis_counts.queued ?? 0} queued`} />
            <Metric label="Queue activity" value={queued} detail={`${data?.queue_counts.failed ?? 0} failed jobs awaiting review`} />
            <Metric label="Support inbox" value={pendingContacts} detail="New inquiries in this result set" />
          </section>

          <section className="admin-section" id="ledger" hidden={activeSection !== "ledger"}>
            <div className="admin-section-heading">
              <div><span className="admin-eyebrow">EVIDENCE MANAGEMENT</span><h2>Inspection ledger</h2><p>Search all stored inspections by case ID, filename, or account email.</p></div>
              <span className="admin-count-chip">{analysisTotal.toLocaleString()} records</span>
            </div>
            <form className="admin-toolbar" onSubmit={searchLedger}>
              <SearchField value={ledgerQuery} onChange={setLedgerQuery} label="Search inspection ledger" placeholder="Search case ID, filename, or user email" />
              <select className="admin-select" aria-label="Filter inspections by status" value={ledgerStatus} onChange={(event) => setLedgerStatus(event.target.value)}>
                <option value="">All statuses</option><option value="queued">Queued</option><option value="processing">Processing</option><option value="completed">Completed</option><option value="failed">Failed</option>
              </select>
              <button className="button button-primary" type="submit" disabled={busy}>Search ledger</button>
            </form>
            <div className="admin-record-list">
              {analyses.map((record) => (
                <article className="admin-record-card" key={record.analysis_id}>
                  <div className="admin-record-main">
                    <div className="admin-record-icon" aria-hidden="true">{record.file.detected_mime_type.startsWith("video/") ? "▶" : "▧"}</div>
                    <div className="admin-record-title"><strong title={record.file.original_filename}>{record.file.original_filename}</strong><small>{record.analysis_id.toUpperCase()} · {record.file.detected_mime_type}</small></div>
                  </div>
                  <div className="admin-record-fact"><span>Account</span><strong title={record.owner_email ?? ""}>{record.owner_name || "Account"}<small>{record.owner_email || "No account details"}</small></strong></div>
                  <div className="admin-record-fact"><span>Result</span><strong>{record.summary.classification.replaceAll("_", " ")}{record.summary.confidence_value !== null && <small>{(record.summary.confidence_value * 100).toFixed(1)}% screening score</small>}</strong></div>
                  <div className="admin-record-fact"><span>Created</span><strong>{formatDate(record.created_at)}<small>{formatBytes(record.file.size_bytes)} · {record.file.width} × {record.file.height}px</small></strong></div>
                  <div className="admin-record-side"><span className={`admin-state ${statusClass(record.status)}`}>{record.status.replaceAll("_", " ")}</span><details className="admin-record-disclosure"><summary>Record details</summary><div><p>{record.summary.explanation}</p><code>SHA-256 {record.file.sha256}</code></div></details></div>
                </article>
              ))}
              {!analyses.length && <div className="admin-empty-state"><strong>No matching inspections</strong><span>Adjust the search or clear the status filter.</span></div>}
            </div>
            <div className="admin-pagination"><span>Page {ledgerPage} of {ledgerPageCount} · {analysisTotal.toLocaleString()} records</span><div><button className="button button-small button-outline" type="button" disabled={busy || ledgerPage <= 1} onClick={() => void changeLedgerPage(ledgerPage - 1)}>Previous</button><button className="button button-small button-outline" type="button" disabled={busy || ledgerPage >= ledgerPageCount} onClick={() => void changeLedgerPage(ledgerPage + 1)}>Next</button></div></div>
            <p className="admin-section-footnote">Records remain owned by their original account. Media bytes are never exposed by this management view.</p>
          </section>

          <section className="admin-section" id="users" hidden={activeSection !== "users"}>
            <div className="admin-section-heading">
              <div><span className="admin-eyebrow">ACCOUNT MANAGEMENT</span><h2>User management</h2><p>Review signup details, ban access, or remove a user account and its stored inspections.</p></div>
              <span className="admin-count-chip">{userTotal.toLocaleString()} accounts</span>
            </div>
            <form className="admin-toolbar" onSubmit={searchUsers}>
              <SearchField value={userQuery} onChange={setUserQuery} label="Search users" placeholder="Search name, email, username, or phone" />
              <button className="button button-primary" type="submit" disabled={busy}>Search users</button>
            </form>
            <div className="admin-card-list admin-user-management-list">
              {users.map((user) => <article className="admin-user-card admin-user-management-card" key={user.id}>
                <div className="admin-user-profile">
                  <div className="admin-user-avatar" aria-hidden="true">{user.display_name.slice(0, 1).toUpperCase()}</div>
                  <div className="admin-user-identity"><strong>{user.display_name}</strong><span>{user.email}</span><small>{user.username ? `@${user.username}` : "No username"} · joined {formatDate(user.created_at)}</small></div>
                </div>
                <span className={`admin-state ${statusClass(user.active ? "active" : "disabled")}`}>{user.active ? "Active" : "Banned"}</span>
                <dl className="admin-user-details">
                  <div><dt>Phone</dt><dd>{user.phone_number || "Not provided"}</dd></div>
                  <div><dt>Signup method</dt><dd>{user.signup_method.replaceAll("_", " ")}</dd></div>
                  <div><dt>Signup IP</dt><dd>{user.signup_ip || "Not recorded for this account"}</dd></div>
                  <div><dt>Email</dt><dd>{user.email_verified ? "Verified" : "Unverified"}</dd></div>
                  <div><dt>Inspections</dt><dd>{user.analysis_count.toLocaleString()}</dd></div>
                </dl>
                <div className="admin-card-actions">
                  <button className="button button-small button-outline" type="button" disabled={busyId === user.id} onClick={() => void updateUser(user, !user.active)}>{busyId === user.id ? "Updating…" : user.active ? "Ban user" : "Unban user"}</button>
                  <button className="button button-small button-outline-danger" type="button" disabled={busyId === user.id} onClick={() => { setDeleteTarget(user); setDeleteConfirmation(""); }}>Delete user</button>
                </div>
              </article>)}
              {!users.length && <div className="admin-empty-state"><strong>No matching users</strong><span>Try another name, email, username, or phone number.</span></div>}
            </div>
            {deleteTarget && <article className="admin-confirm-panel admin-danger-card">
              <div><span className="admin-eyebrow">PERMANENT ACCOUNT REMOVAL</span><h3>Delete {deleteTarget.display_name}?</h3><p>This permanently removes the account, sessions, inspections, and stored media. Type the exact phrase below to continue.</p></div>
              <label className="admin-confirm-field"><span>Type <strong>{`DELETE USER ${deleteTarget.email}`}</strong></span><input value={deleteConfirmation} onChange={(event) => setDeleteConfirmation(event.target.value)} autoComplete="off" /></label>
              <div className="admin-card-actions"><button className="button button-outline-danger" type="button" disabled={busyId === deleteTarget.id || deleteConfirmation !== `DELETE USER ${deleteTarget.email}`} onClick={() => void deleteUser()}>{busyId === deleteTarget.id ? "Deleting…" : "Permanently delete user"}</button><button className="button button-small button-outline" type="button" onClick={() => { setDeleteTarget(null); setDeleteConfirmation(""); }}>Cancel</button></div>
            </article>}
            <div className="admin-pagination"><span>Page {userPage} of {userPageCount} · {userTotal.toLocaleString()} users</span><div><button className="button button-small button-outline" type="button" disabled={busy || userPage <= 1} onClick={() => void changeUserPage(userPage - 1)}>Previous</button><button className="button button-small button-outline" type="button" disabled={busy || userPage >= userPageCount} onClick={() => void changeUserPage(userPage + 1)}>Next</button></div></div>
            <p className="admin-section-footnote">Signup IP is shown only to administrators. Existing accounts without a saved signup address display “Not recorded.”</p>
          </section>

          <section className="admin-section" id="control" hidden={activeSection !== "control"}>
            <div className="admin-section-heading">
              <div><span className="admin-eyebrow">PLATFORM OPERATIONS</span><h2>Control panel</h2><p>Monitor forensic services and manage the processing queue.</p></div>
            </div>
            <div className="admin-health-grid">
              <article className="admin-health-card"><span className="admin-health-icon">◎</span><div><small>Image forensics</small><strong>{data?.detector.status ?? "unknown"}</strong><span>{data?.detector.model_id ?? "No model identifier"}{data?.detector.model_version ? ` · ${data.detector.model_version}` : ""}</span></div><i className={statusClass(data?.detector.status ?? "unknown")} /></article>
              <article className="admin-health-card"><span className="admin-health-icon">◷</span><div><small>Background workers</small><strong>{data?.worker.status ?? "unknown"}</strong><span>{data?.worker.active_workers ?? 0} active worker processes</span></div><i className={statusClass(data?.worker.status ?? "unknown")} /></article>
              <article className="admin-health-card"><span className="admin-health-icon">▤</span><div><small>Inference queue</small><strong>{queued} waiting or running</strong><span>{data?.queue_counts.completed ?? 0} jobs completed</span></div><i className="is-running" /></article>
            </div>

            <div className="admin-subsection">
              <div className="admin-subsection-heading"><div><h3>Processing queue</h3><p>Review stuck or failed work and safely requeue eligible records.</p></div><span className="admin-count-chip">{jobs.length} recent</span></div>
              <div className="admin-card-list">
                {jobs.map((job) => <article className="admin-job-card" key={job.id}>
                  <div className="admin-record-title"><strong>Inspection {job.analysis_id.slice(0, 12).toUpperCase()}</strong><small>Job {job.id.slice(0, 12)} · {formatDate(job.created_at)}</small></div>
                  <span className={`admin-state ${statusClass(job.status)}`}>{job.status}</span>
                  <span className="admin-job-detail">Attempt {job.attempts} of 3</span>
                  <span className="admin-job-detail" title={job.last_error ?? "No error recorded"}>{job.last_error || "No error recorded"}</span>
                  <button className="button button-small button-outline" type="button" disabled={busyId === job.id || !["failed", "completed"].includes(job.status)} onClick={() => void retryJob(job)}>{busyId === job.id ? "Queueing…" : "Run again"}</button>
                </article>)}
                {!jobs.length && <div className="admin-empty-state">No recent processing jobs.</div>}
              </div>
            </div>

          </section>

          <section className="admin-section" id="contacts" hidden={activeSection !== "contacts"}>
            <div className="admin-section-heading">
              <div><span className="admin-eyebrow">USER SUPPORT</span><h2>Contact inbox</h2><p>Review the details users submitted and track each query through resolution.</p></div>
              <span className="admin-count-chip">{pendingContacts} new</span>
            </div>
            <form className="admin-toolbar" onSubmit={searchContacts}>
              <SearchField value={contactQuery} onChange={setContactQuery} label="Search contact inquiries" placeholder="Search name, email, topic, or message" />
              <select className="admin-select" aria-label="Filter contact inquiries" value={contactStatus} onChange={(event) => setContactStatus(event.target.value)}><option value="">All inquiries</option><option value="new">New</option><option value="in_progress">In progress</option><option value="resolved">Resolved</option></select>
              <button className="button button-primary" type="submit" disabled={busy}>Search inbox</button>
            </form>
            <div className="admin-inquiry-list">
              {inquiries.map((inquiry) => <article className="admin-inquiry-card" key={inquiry.id}>
                <div className="admin-inquiry-heading"><div><span className="admin-eyebrow">{inquiry.topic}</span><h3>{inquiry.name}</h3><a href={`mailto:${inquiry.email}`}>{inquiry.email}</a></div><div className="admin-inquiry-status"><time>{formatDate(inquiry.created_at)}</time><span className={`admin-state ${statusClass(inquiry.status)}`}>{inquiry.status.replaceAll("_", " ")}</span></div></div>
                <p className="admin-inquiry-message">{inquiry.message}</p>
                <div className="admin-inquiry-actions"><label className="admin-status-control"><span>Status</span><select aria-label={`Status for inquiry from ${inquiry.name}`} value={inquiry.status} disabled={busyId === inquiry.id} onChange={(event) => void updateInquiry(inquiry, { status: event.target.value as ContactInquiry["status"] })}><option value="new">New</option><option value="in_progress">In progress</option><option value="resolved">Resolved</option></select></label>
                  <form className="admin-note-form" onSubmit={(event) => { event.preventDefault(); void updateInquiry(inquiry, { admin_note: noteDrafts[inquiry.id] ?? inquiry.admin_note ?? "" }); }}><label htmlFor={`inquiry-note-${inquiry.id}`}>Internal note</label><input id={`inquiry-note-${inquiry.id}`} value={noteDrafts[inquiry.id] ?? inquiry.admin_note ?? ""} onChange={(event) => setNoteDrafts((current) => ({ ...current, [inquiry.id]: event.target.value }))} placeholder="Add a private follow-up note" /><button className="button button-small button-outline" type="submit" disabled={busyId === inquiry.id}>Save note</button></form>
                </div>
              </article>)}
              {!inquiries.length && <div className="admin-empty-state"><strong>Your contact inbox is clear</strong><span>New user submissions will appear here with their name, email, topic, and message.</span></div>}
            </div>
            <div className="admin-pagination"><span>Page {contactPage} of {contactPageCount} · {contactTotal.toLocaleString()} inquiries</span><div><button className="button button-small button-outline" type="button" disabled={busy || contactPage <= 1} onClick={() => void changeContactPage(contactPage - 1)}>Previous</button><button className="button button-small button-outline" type="button" disabled={busy || contactPage >= contactPageCount} onClick={() => void changeContactPage(contactPage + 1)}>Next</button></div></div>
          </section>

          <section className="admin-section" id="admins" hidden={activeSection !== "admins"}>
            <div className="admin-section-heading"><div><span className="admin-eyebrow">STAFF ACCESS</span><h2>Admin management</h2><p>Promote a verified account or invite a new administrator through a one-time email link.</p></div><span className="admin-count-chip">{adminAccounts.length} administrators</span></div>
            <article className="admin-settings-card admin-admin-create-card">
              <div className="admin-settings-card-heading"><span className="admin-settings-icon">＋</span><div><h3>Add an administrator</h3><p>Enter an email to promote an eligible verified account or send a new one-time setup invitation.</p></div></div>
              <form className="admin-toolbar admin-invite-form" onSubmit={inviteAdmin}>
                <label className="admin-form-field"><span>Administrator email</span><input type="email" required value={adminInviteEmail} onChange={(event) => setAdminInviteEmail(event.target.value)} placeholder="name@company.com" autoComplete="email" /></label>
                <button className="button button-primary" type="submit" disabled={busyId === "admin-invite" || !adminInviteEmail.trim()}>{busyId === "admin-invite" ? "Creating invite…" : "Create or invite admin"}</button>
              </form>
              <p className="admin-section-footnote">Existing accounts must be active and email-verified. New invitations expire after 24 hours.</p>
            </article>
            {adminInviteUrl && <article className="admin-admin-invite-link" role="status">
              <div><span className="admin-eyebrow">EMAIL DELIVERY UNAVAILABLE</span><h3>Secure setup link created</h3><p>This link works once and expires after 24 hours. Share it only with the intended administrator.</p></div>
              <label className="admin-form-field"><span>One-time administrator setup link</span><input type="text" readOnly value={adminInviteUrl} onFocus={(event) => event.currentTarget.select()} /></label>
              <button className="button button-primary" type="button" onClick={() => void copyAdminInviteUrl()}>Copy setup link</button>
            </article>}
            <form className="admin-toolbar" onSubmit={searchAdminAccounts}>
              <SearchField value={adminQuery} onChange={setAdminQuery} label="Search administrators" placeholder="Search administrator name, username, or email" />
              <button className="button button-outline" type="submit" disabled={busy}>Search admins</button>
            </form>
            <div className="admin-subsection">
              <div className="admin-subsection-heading"><div><h3>Administrator accounts</h3><p>Review staff status and role controls.</p></div><span className="admin-count-chip">{adminAccounts.length} accounts</span></div>
              <div className="admin-card-list">
                {adminAccounts.map((account) => <article className="admin-user-card admin-admin-card" key={account.id}>
                  <div className="admin-user-profile"><div className="admin-user-avatar" aria-hidden="true">{account.display_name.slice(0, 1).toUpperCase()}</div><div className="admin-user-identity"><strong>{account.display_name}</strong><span>{account.email}</span><small>{account.username ? `@${account.username}` : "No username"} · {account.email_verified ? "Verified" : "Unverified"}</small></div></div>
                  <span className={`admin-state ${statusClass(account.active ? "active" : "disabled")}`}>{account.active ? "Active" : "Disabled"}</span>
                  <span className="admin-user-meta">Joined {formatDate(account.created_at)}{account.phone_number ? ` · ${account.phone_number}` : " · No phone number"}</span>
                  <div className="admin-card-actions">{account.protected ? <span className="admin-protected-note">Protected bootstrap account</span> : <>
                    <button className="button button-small button-outline" type="button" disabled={busyId === account.id} onClick={() => void updateAdmin(account, account.active ? "disable" : "restore")}>{account.active ? "Disable" : "Restore"}</button>
                    <button className="button button-small button-outline-danger" type="button" disabled={busyId === account.id} onClick={() => { setAdminActionTarget(account); setAdminActionConfirmation(""); }}>Revoke admin role</button>
                  </>}</div>
                </article>)}
                {!adminAccounts.length && <div className="admin-empty-state">No administrator accounts found.</div>}
              </div>
            </div>
            {adminActionTarget && <article className="admin-confirm-panel admin-danger-card">
              <div><span className="admin-eyebrow">ADMIN ROLE CHANGE</span><h3>Revoke administrator access?</h3><p>{adminActionTarget.email} will become a regular user and all of their sessions will be revoked.</p></div>
              <label className="admin-confirm-field"><span>Type <strong>{`REVOKE ADMIN ${adminActionTarget.email}`}</strong></span><input value={adminActionConfirmation} onChange={(event) => setAdminActionConfirmation(event.target.value)} autoComplete="off" /></label>
              <div className="admin-card-actions"><button className="button button-outline-danger" type="button" disabled={busyId === adminActionTarget.id || adminActionConfirmation !== `REVOKE ADMIN ${adminActionTarget.email}`} onClick={() => void updateAdmin(adminActionTarget, "revoke")}>{busyId === adminActionTarget.id ? "Revoking…" : "Revoke admin access"}</button><button className="button button-small button-outline" type="button" onClick={() => { setAdminActionTarget(null); setAdminActionConfirmation(""); }}>Cancel</button></div>
            </article>}
            <div className="admin-subsection">
              <div className="admin-subsection-heading"><div><h3>Pending invitations</h3><p>Unused links expire automatically after 24 hours.</p></div><span className="admin-count-chip">{adminInvitations.length} pending</span></div>
              <div className="admin-card-list">{adminInvitations.map((invitation) => <article className="admin-admin-invitation" key={invitation.id}><div><strong>{invitation.email}</strong><small>Sent {formatDate(invitation.created_at)} · expires {formatDate(invitation.expires_at)}</small></div><button className="button button-small button-outline-danger" type="button" disabled={busyId === invitation.id} onClick={() => void cancelAdminInvitation(invitation)}>{busyId === invitation.id ? "Canceling…" : "Cancel invite"}</button></article>)}{!adminInvitations.length && <div className="admin-empty-state">No pending administrator invitations.</div>}</div>
            </div>
          </section>

          <section className="admin-section" id="user-logs" hidden={activeSection !== "user-logs"}>
            <div className="admin-section-heading"><div><span className="admin-eyebrow">ACCOUNT ACTIVITY</span><h2>User logs</h2><p>Search account creation, login, verification, inspection, and account actions.</p></div><span className="admin-count-chip">{userLogTotal.toLocaleString()} entries</span></div>
            <form className="admin-toolbar" onSubmit={searchUserLogs}><SearchField value={userLogQuery} onChange={setUserLogQuery} label="Search user logs" placeholder="Search user, email, action, inspection ID" /><button className="button button-primary" type="submit" disabled={busy}>Search user logs</button></form>
            <div className="admin-audit-list">{userLogs.map((event) => <article className="admin-audit-row" key={event.id}><span className="admin-audit-marker" aria-hidden="true" /><div><strong>{event.action.replaceAll(".", " · ")}</strong><small>{event.actor_name || "Deleted account"}{event.actor_email ? ` · ${event.actor_email}` : ""}{event.subject_id ? ` · ${event.subject_id}` : ""}</small>{Object.keys(event.details).length > 0 && <code>{JSON.stringify(event.details)}</code>}</div><time>{formatDate(event.created_at)}</time></article>)}{!userLogs.length && <div className="admin-empty-state">No user activity matches this search.</div>}</div>
            <div className="admin-pagination"><span>Page {userLogPage} of {userLogPageCount} · {userLogTotal.toLocaleString()} entries</span><div><button className="button button-small button-outline" type="button" disabled={busy || userLogPage <= 1} onClick={() => void changeUserLogPage(userLogPage - 1)}>Previous</button><button className="button button-small button-outline" type="button" disabled={busy || userLogPage >= userLogPageCount} onClick={() => void changeUserLogPage(userLogPage + 1)}>Next</button></div></div>
            <article className="admin-settings-card admin-danger-card admin-log-clear-card"><div><h3>Clear user activity logs</h3><p>Deletes all user activity entries. The purge action is retained in Admin Logs.</p></div><label className="admin-confirm-field"><span>Type <strong>DELETE ALL USER LOGS</strong></span><input value={userLogConfirmation} onChange={(event) => setUserLogConfirmation(event.target.value)} autoComplete="off" /></label><button className="button button-outline-danger" type="button" disabled={busyId === "user-logs-clear" || userLogConfirmation !== "DELETE ALL USER LOGS"} onClick={() => void clearLogs("user")}>{busyId === "user-logs-clear" ? "Clearing…" : "Delete all user logs"}</button></article>
          </section>

          <section className="admin-section" id="admin-logs" hidden={activeSection !== "admin-logs"}>
            <div className="admin-section-heading"><div><span className="admin-eyebrow">PRIVILEGED ACTIONS</span><h2>Admin logs</h2><p>Search administrator sign-ins, user changes, restrictions, and platform actions.</p></div><span className="admin-count-chip">{auditTotal.toLocaleString()} entries</span></div>
            <form className="admin-toolbar" onSubmit={searchAdminLogs}><SearchField value={adminLogQuery} onChange={setAdminLogQuery} label="Search administrator logs" placeholder="Search admin, email, action, record" /><button className="button button-primary" type="submit" disabled={busy}>Search admin logs</button></form>
            <div className="admin-audit-list">{audit.map((event) => <article className="admin-audit-row" key={event.id}><span className="admin-audit-marker" aria-hidden="true" /><div><strong>{event.action.replaceAll(".", " · ")}</strong><small>{event.actor_name || "System event"}{event.actor_email ? ` · ${event.actor_email}` : event.actor_id ? ` · ${event.actor_id.slice(0, 12)}` : ""}{event.subject_id ? ` · ${event.subject_id}` : ""}</small>{Object.keys(event.details).length > 0 && <code>{JSON.stringify(event.details)}</code>}</div><time>{formatDate(event.created_at)}</time></article>)}{!audit.length && <div className="admin-empty-state">No administrator activity matches this search.</div>}</div>
            <div className="admin-pagination"><span>Page {auditPage} of {auditPageCount} · {auditTotal.toLocaleString()} entries</span><div><button className="button button-small button-outline" type="button" disabled={busy || auditPage <= 1} onClick={() => void changeAdminLogPage(auditPage - 1)}>Previous</button><button className="button button-small button-outline" type="button" disabled={busy || auditPage >= auditPageCount} onClick={() => void changeAdminLogPage(auditPage + 1)}>Next</button></div></div>
            <article className="admin-settings-card admin-danger-card admin-log-clear-card"><div><h3>Clear administrator logs</h3><p>Removes previous entries and keeps a new purge record in this administrator audit trail.</p></div><label className="admin-confirm-field"><span>Type <strong>DELETE ALL ADMIN LOGS</strong></span><input value={adminLogConfirmation} onChange={(event) => setAdminLogConfirmation(event.target.value)} autoComplete="off" /></label><button className="button button-outline-danger" type="button" disabled={busyId === "admin-logs-clear" || adminLogConfirmation !== "DELETE ALL ADMIN LOGS"} onClick={() => void clearLogs("admin")}>{busyId === "admin-logs-clear" ? "Clearing…" : "Delete all admin logs"}</button></article>
          </section>

          <section className="admin-section" id="security" hidden={activeSection !== "security"}>
            <div className="admin-section-heading"><div><span className="admin-eyebrow">THREAT RESPONSE</span><h2>Security monitoring</h2><p>Review reported access issues, network restrictions, and security operations.</p></div><span className="admin-count-chip">{ipBlocks.filter((block) => block.status === "blocked").length} active restrictions</span></div>
            <div className="admin-subsection">
              <div className="admin-subsection-heading"><div><h3>Restrict a network address</h3><p>New sign-ins and inspections from this address will follow the platform’s IP restriction policy.</p></div></div>
              <form className="admin-toolbar admin-network-form" onSubmit={blockNetwork}><label className="admin-form-field"><span>IPv4 or IPv6 address</span><input required value={securityIp} onChange={(event) => setSecurityIp(event.target.value)} placeholder="203.0.113.10" autoComplete="off" /></label><label className="admin-form-field"><span>Reason</span><input value={securityIpReason} onChange={(event) => setSecurityIpReason(event.target.value)} placeholder="Abuse or policy reason" maxLength={240} /></label><button className="button button-primary" type="submit" disabled={busyId === "security-block-ip"}>{busyId === "security-block-ip" ? "Applying…" : "Block address"}</button></form>
            </div>
            <div className="admin-security-grid">
              <article className="admin-settings-card"><div className="admin-settings-card-heading"><span className="admin-settings-icon">⌑</span><div><h3>Pending access requests</h3><p>Requests submitted by users affected by a network restriction.</p></div></div><div className="admin-security-group">{unblockRequests.map((request) => <div className="admin-security-item" key={request.id}><div><b>{request.name}</b><small>{request.email} · {request.reference_id}</small><p>{request.reason}</p></div><div className="admin-card-actions"><button className="button button-small button-outline" disabled={busyId === request.id} type="button" onClick={() => void resolveRequest(request, "approved")}>Approve</button><button className="button button-small button-outline-danger" disabled={busyId === request.id} type="button" onClick={() => void resolveRequest(request, "rejected")}>Reject</button></div></div>)}{!unblockRequests.length && <small className="admin-muted">No pending access requests.</small>}</div></article>
              <article className="admin-settings-card"><div className="admin-settings-card-heading"><span className="admin-settings-icon">⛨</span><div><h3>Active network restrictions</h3><p>Restrictions are stored as keyed hashes; raw addresses are not shown here.</p></div></div><div className="admin-security-group">{ipBlocks.filter((block) => block.status === "blocked").map((block) => <div className="admin-security-item" key={block.id}><div><b>{block.reference_id}</b><small>{block.reason} · {block.linked_accounts.length} linked account(s)</small><p>{block.linked_accounts.map((item) => item.email).join(", ") || "No linked accounts"}</p></div><button className="button button-small button-outline" type="button" disabled={busyId === block.id} onClick={() => void unblockIp(block)}>{busyId === block.id ? "Updating…" : "Unblock"}</button></div>)}{!ipBlocks.some((block) => block.status === "blocked") && <small className="admin-muted">No active network restrictions.</small>}</div></article>
            </div>
          </section>

          <section className="admin-section" id="traffic" hidden={activeSection !== "traffic"}>
            <div className="admin-section-heading"><div><span className="admin-eyebrow">NETWORK OPERATIONS</span><h2>Traffic management</h2><p>Review the events the platform records and manage trusted network exceptions.</p></div><span className="admin-count-chip">Last {traffic?.window_hours ?? 24} hours</span></div>
            <div className="admin-metric-grid admin-traffic-metrics"><Metric label="Tracked access events" value={traffic?.access_events_24h ?? 0} detail="Security and support events recorded" /><Metric label="Inspections started" value={traffic?.inspections_24h ?? 0} detail="Inspection records created" /><Metric label="New accounts" value={traffic?.signups_24h ?? 0} detail="Accounts created in this period" /><Metric label="Active rate limits" value={traffic?.active_rate_limit_buckets ?? 0} detail={`${traffic?.expired_rate_limit_buckets ?? 0} expired counters ready to clear`} /></div>
            <div className="admin-traffic-grid">
              <article className="admin-settings-card"><div className="admin-settings-card-heading"><span className="admin-settings-icon">⌁</span><div><h3>Access event breakdown</h3><p>These are recorded security and support events, not a count of every HTTP request.</p></div></div><div className="admin-traffic-events">{traffic?.event_breakdown.map((item) => <div key={item.action}><span>{item.action.replaceAll(".", " · ")}</span><strong>{item.count.toLocaleString()}</strong></div>)}{!traffic?.event_breakdown.length && <small className="admin-muted">No tracked access events in the last day.</small>}</div></article>
              <article className="admin-settings-card"><div className="admin-settings-card-heading"><span className="admin-settings-icon">✦</span><div><h3>Allow a trusted network</h3><p>Allowlisting bypasses automatic IP restrictions for this exact address.</p></div></div><form className="admin-network-form admin-network-form--stacked" onSubmit={allowNetwork}><label className="admin-form-field"><span>IPv4 or IPv6 address</span><input required value={trafficIp} onChange={(event) => setTrafficIp(event.target.value)} placeholder="203.0.113.10" autoComplete="off" /></label><label className="admin-form-field"><span>Reason</span><input value={trafficIpReason} onChange={(event) => setTrafficIpReason(event.target.value)} placeholder="Optional reason" maxLength={240} /></label><button className="button button-primary" type="submit" disabled={busyId === "traffic-allow-ip"}>{busyId === "traffic-allow-ip" ? "Saving…" : "Add to allowlist"}</button></form></article>
            </div>
            <article className="admin-settings-card admin-allowlist-card"><div className="admin-settings-card-heading"><div><h3>Trusted network allowlist</h3><p>Addresses are represented by one-way keyed fingerprints.</p></div><span className="admin-count-chip">{allowlistedNetworks.length} entries</span></div><div className="admin-card-list">{allowlistedNetworks.map((entry) => <article className="admin-admin-invitation" key={entry.ip_hash}><div><strong>Network {entry.fingerprint}</strong><small>{entry.reason || "No reason provided"} · added {formatDate(entry.created_at)}</small></div><button className="button button-small button-outline-danger" type="button" disabled={busyId === entry.ip_hash} onClick={() => void removeAllowedNetwork(entry)}>{busyId === entry.ip_hash ? "Removing…" : "Remove"}</button></article>)}{!allowlistedNetworks.length && <div className="admin-empty-state">No networks are allowlisted.</div>}</div></article>
            <article className="admin-settings-card admin-danger-card admin-log-clear-card"><div><h3>Clear expired traffic counters</h3><p>Only expired rate-limit windows are removed; active limits are untouched.</p></div><label className="admin-confirm-field"><span>Type <strong>CLEAR EXPIRED TRAFFIC COUNTERS</strong></span><input value={trafficCleanupConfirmation} onChange={(event) => setTrafficCleanupConfirmation(event.target.value)} autoComplete="off" /></label><button className="button button-outline-danger" type="button" disabled={busyId === "traffic-cleanup" || trafficCleanupConfirmation !== "CLEAR EXPIRED TRAFFIC COUNTERS"} onClick={() => void clearExpiredTraffic()}>{busyId === "traffic-cleanup" ? "Clearing…" : "Clear expired counters"}</button></article>
          </section>

          <section className="admin-section" id="settings" hidden={activeSection !== "settings"}>
            <div className="admin-section-heading"><div><span className="admin-eyebrow">PLATFORM CONFIGURATION</span><h2>Settings</h2><p>Control platform availability and manage administrator security actions.</p></div></div>
            <div className="admin-settings-grid">
              <article className="admin-settings-card">
                <div className="admin-settings-card-heading"><span className="admin-settings-icon">⚙</span><div><h3>Platform features</h3><p>Changes take effect immediately at the API.</p></div></div>
                <label className="admin-toggle-row"><span><strong>New account registration</strong><small>Allow users to create new accounts.</small></span><input type="checkbox" checked={settings.registration_enabled} onChange={(event) => setSettings((current) => ({ ...current, registration_enabled: event.target.checked }))} /></label>
                <label className="admin-toggle-row"><span><strong>New inspections</strong><small>Allow verified accounts to start an inspection.</small></span><input type="checkbox" checked={settings.inspections_enabled} onChange={(event) => setSettings((current) => ({ ...current, inspections_enabled: event.target.checked }))} /></label>
                <label className="admin-confirm-field"><span>Type <strong>APPLY PLATFORM SETTINGS</strong> to save</span><input value={settingsConfirmation} onChange={(event) => setSettingsConfirmation(event.target.value)} autoComplete="off" /></label>
                <button className="button button-primary" type="button" disabled={busyId === "settings" || settingsConfirmation !== "APPLY PLATFORM SETTINGS"} onClick={() => void saveSettings()}>{busyId === "settings" ? "Saving…" : "Save settings"}</button>
              </article>

              <article className="admin-settings-card admin-danger-card">
                <div className="admin-settings-card-heading"><span className="admin-settings-icon">!</span><div><h3>Danger zone</h3><p>Revoke other active sessions on this administrator account. Your current session stays active.</p></div></div>
                <label className="admin-confirm-field"><span>Type <strong>REVOKE OTHER SESSIONS</strong> to continue</span><input value={dangerConfirmation} onChange={(event) => setDangerConfirmation(event.target.value)} autoComplete="off" /></label>
                <button className="button button-outline-danger" type="button" disabled={busyId === "revoke-sessions" || dangerConfirmation !== "REVOKE OTHER SESSIONS"} onClick={() => void revokeOtherSessions()}>{busyId === "revoke-sessions" ? "Revoking…" : "Revoke other sessions"}</button>
              </article>
            </div>
            <p className="admin-footer-note">{data?.note} Administrative actions are recorded in the platform audit trail.</p>
          </section>
        </>
      )}
    </div>
  );
}
