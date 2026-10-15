"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type User } from "@/lib/api";
import { Brand } from "@/components/brand";
import { ThemeToggle } from "@/components/theme-toggle";
import { Tooltip } from "@/components/tooltip";

const navItems = [
  {
    href: "/app",
    label: "Overview",
    sub: "Telemetry & summary",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
      </svg>
    ),
  },
  {
    href: "/app/analyze",
    label: "New Inspection",
    sub: "Neural studio scan",
    badge: "STUDIO",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7" />
        <line x1="16" y1="5" x2="22" y2="5" />
        <line x1="19" y1="2" x2="19" y2="8" />
        <circle cx="9" cy="9" r="2" />
        <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" />
      </svg>
    ),
  },
  {
    href: "/app/history",
    label: "Inspection Ledger",
    sub: "Evidence records",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
    ),
  },
  {
    href: "/app/settings",
    label: "Account & Keys",
    sub: "Retention & security",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
      </svg>
    ),
  },
];

const adminNavGroups = [
  { label: "Command", items: [
    { id: "overview", label: "Overview", sub: "Platform status" },
  ] },
  { label: "Management", items: [
    { id: "ledger", label: "Inspection ledger", sub: "Evidence records" },
    { id: "users", label: "User management", sub: "Accounts & access" },
    { id: "admins", label: "Admin management", sub: "Staff access" },
    { id: "contacts", label: "Contact inbox", sub: "User support queries" },
  ] },
  { label: "Operations", items: [
    { id: "control", label: "Control panel", sub: "Models & queue" },
    { id: "security", label: "Security monitoring", sub: "Restrictions & requests" },
    { id: "traffic", label: "Traffic management", sub: "Networks & rate limits" },
  ] },
  { label: "Audit trail", items: [
    { id: "user-logs", label: "User logs", sub: "Account activity" },
    { id: "admin-logs", label: "Admin logs", sub: "Privileged actions" },
  ] },
  { label: "Platform", items: [
    { id: "settings", label: "Settings", sub: "Platform & safeguards" },
  ] },
];

function AdminNavGlyph({ id }: { id: string }) {
  const paths: Record<string, React.ReactNode> = {
    overview: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    ledger: <><path d="M5 4h14v16H5z" /><path d="M8 8h8M8 12h8M8 16h5" /></>,
    users: <><circle cx="9" cy="8" r="3" /><path d="M3 20v-1a6 6 0 0 1 12 0v1z" /><path d="M16 5.5a3 3 0 0 1 0 5.8M18 14a5 5 0 0 1 3 4.6V20" /></>,
    control: <><path d="M4 19V5M4 19h16" /><path d="m7 15 4-4 3 2 5-6" /></>,
    contacts: <><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m4 7 8 6 8-6" /></>,
    "user-logs": <><path d="M4 19V5M4 19h16" /><path d="M7 15l3-4 3 2 4-6" /></>,
    "admin-logs": <><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><path d="m9 12 2 2 4-4" /></>,
    admins: <><circle cx="12" cy="8" r="3" /><path d="M5 20v-1a7 7 0 0 1 14 0v1" /><path d="M19 8h3M20.5 6.5v3" /></>,
    security: <><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><path d="M12 8v4m0 4h.01" /></>,
    traffic: <><path d="M3 19h18" /><path d="M6 16v-5m6 5V5m6 11v-8" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="m19.4 15 .1.1a2 2 0 1 1-2.8 2.8l-.1-.1a2 2 0 0 0-3.4 1.4v.2a2 2 0 1 1-4 0v-.2A2 2 0 0 0 5.8 18l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a2 2 0 0 0-1.4-3.4H1.5a2 2 0 1 1 0-4h.2A2 2 0 0 0 3.1 6l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a2 2 0 0 0 3.4-1.4v-.2a2 2 0 1 1 4 0v.2A2 2 0 0 0 16.7 3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a2 2 0 0 0 1.4 3.4h.2a2 2 0 1 1 0 4h-.2a2 2 0 0 0-1.4 1.8z" /></>,
  };
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[id]}</svg>;
}

export function AuthGuard({ children, admin = false }: { children: React.ReactNode; admin?: boolean }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [guestAllowed, setGuestAllowed] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [adminSection, setAdminSection] = useState("overview");
  const router = useRouter();
  const pathname = usePathname();
  const publicGuestPage = pathname === "/app/analyze" || /^\/app\/analyses\/[a-f0-9]{32}$/.test(pathname || "");

  useEffect(() => {
    let active = true;
    setReady(false);
    setGuestAllowed(false);
    api<User>("/auth/me")
      .then((result) => {
        if (!active) return;
        setUser(result);
        if (admin && result.role !== "admin") router.replace("/app");
      })
      .catch(() => {
        if (!active) return;
        setUser(null);
        if (publicGuestPage && !admin) setGuestAllowed(true);
        else router.replace((admin ? "/sign-in?next=" : "/login?next=") + encodeURIComponent(pathname));
      })
      .finally(() => { if (active) setReady(true); });
    return () => { active = false; };
  }, [admin, pathname, publicGuestPage, router]);

  useEffect(() => {
    setMobileNavOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!admin) return;
    const updateSection = () => setAdminSection(decodeURIComponent(window.location.hash.slice(1) || "overview"));
    updateSection();
    window.addEventListener("hashchange", updateSection);
    return () => window.removeEventListener("hashchange", updateSection);
  }, [admin]);

  async function signOut() {
    await api<void>("/auth/logout", { method: "POST" }).catch(() => undefined);
    router.replace(admin ? "/sign-in" : "/login");
  }

  if (!ready || (user && admin && user.role !== "admin")) {
    return (
      <div className="auth-loading">
        <Brand />
        <div className="auth-loading-spinner" aria-hidden="true" />
        <span>Initializing secure workspace session…</span>
      </div>
    );
  }

  if (!user && guestAllowed && !admin) {
    return (
      <div className="guest-workspace">
        <header className="guest-workspace-header">
          <Brand />
          <nav aria-label="Account">
            <Link href={`/login?next=${encodeURIComponent(pathname || "/app/analyze")}`}>Login</Link>
            <Link href={`/register?next=${encodeURIComponent(pathname || "/app/analyze")}`}>Register</Link>
          </nav>
        </header>
        <main className="guest-workspace-content">{children}</main>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className={`app-shell ${admin ? "is-admin-shell" : ""} ${admin && sidebarCollapsed ? "is-admin-collapsed" : ""}`}>
      {/* Mobile drawer backdrop */}
      {mobileNavOpen && (
        <div
          className="app-sidebar-backdrop"
          onClick={() => setMobileNavOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Redesigned Sidebar */}
      <aside className={`app-sidebar ${admin ? "is-admin-sidebar" : ""} ${sidebarCollapsed && admin ? "is-collapsed" : ""} ${mobileNavOpen ? "is-open" : ""}`}>
        <div className={`sidebar-top${admin ? " admin-sidebar-top" : ""}`}>
          <div className="sidebar-brand-cluster">
            <Brand />
            {admin
              ? <div className="admin-sidebar-brand-info"><strong>Admin console</strong><span>Secure operations</span></div>
              : <span className="sidebar-version-pill">CORE v2.4</span>}
          </div>
          {admin && (
            <button
              type="button"
              className="admin-sidebar-toggle"
              onClick={() => setSidebarCollapsed((collapsed) => !collapsed)}
              aria-label={sidebarCollapsed ? "Expand administrator navigation" : "Collapse administrator navigation"}
              aria-expanded={!sidebarCollapsed}
              title={sidebarCollapsed ? "Expand navigation" : "Collapse navigation"}
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="m15 18-6-6 6-6" />
              </svg>
            </button>
          )}
          <button
            type="button"
            className="sidebar-close-btn"
            onClick={() => setMobileNavOpen(false)}
            aria-label="Close menu"
          >
            ×
          </button>
        </div>

        <div className={`sidebar-section${admin ? " admin-sidebar-section" : ""}`}>
          {admin ? (
            <>
              <div className="admin-sidebar-nav-heading">
                <span>Administrator workspace</span>
                <span>{adminNavGroups.reduce((total, group) => total + group.items.length, 0)} sections</span>
              </div>
              <nav className="sidebar-nav admin-sidebar-nav" aria-label="Administrator navigation">
                {adminNavGroups.map((group) => (
                  <div className="admin-nav-group" key={group.label}>
                    <span className="admin-nav-group-label">{group.label}</span>
                    {group.items.map((item) => (
                      <Link
                        key={item.id}
                        href={`/admin#${item.id}`}
                        title={sidebarCollapsed ? item.label : undefined}
                        aria-label={sidebarCollapsed ? item.label : undefined}
                        className={`sidebar-nav-link admin-sidebar-link ${adminSection === item.id ? "is-active" : ""}`}
                        aria-current={adminSection === item.id ? "location" : undefined}
                        onClick={() => {
                          setAdminSection(item.id);
                          window.dispatchEvent(new CustomEvent("cgs:admin-section-change", { detail: item.id }));
                          setMobileNavOpen(false);
                        }}
                      >
                        <span className="nav-icon admin-nav-symbol"><AdminNavGlyph id={item.id} /></span>
                        <div className="nav-label-box">
                          <span className="nav-text">{item.label}</span>
                          <span className="nav-sub">{item.sub}</span>
                        </div>
                        {adminSection === item.id && <span className="nav-indicator" aria-hidden="true" />}
                      </Link>
                    ))}
                  </div>
                ))}
              </nav>
            </>
          ) : (
            <>
              <div className="sidebar-label-row">
                <span className="sidebar-label">WORKSPACE MODULES</span>
                <span className="sidebar-live-tag">SECURE</span>
              </div>
              <nav className="sidebar-nav" aria-label="Workspace navigation">
                {navItems.map((item) => {
                  const active = pathname === item.href;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`sidebar-nav-link ${active ? "is-active" : ""}`}
                      aria-current={active ? "page" : undefined}
                    >
                      <span className="nav-icon">{item.icon}</span>
                      <div className="nav-label-box">
                        <span className="nav-text">{item.label}</span>
                        <span className="nav-sub">{item.sub}</span>
                      </div>
                      {item.badge && <span className="nav-item-badge">{item.badge}</span>}
                      {active && <span className="nav-indicator" aria-hidden="true" />}
                    </Link>
                  );
                })}

                {user.role === "admin" && (
                  <Link href="/admin" className={`sidebar-nav-link sidebar-nav-admin ${pathname === "/admin" ? "is-active" : ""}`} aria-current={pathname === "/admin" ? "page" : undefined}>
                    <span className="nav-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><circle cx="12" cy="11" r="2" /><line x1="12" y1="13" x2="12" y2="16" /></svg></span>
                    <div className="nav-label-box"><span className="nav-text">Control Plane</span><span className="nav-sub">Staff security gate</span></div>
                    <span className="admin-pill">STAFF</span>
                  </Link>
                )}
              </nav>
            </>
          )}
        </div>

        <div className="sidebar-spacer" />

        {/* Live Forensic Telemetry Widget */}
        <div className="sidebar-telemetry-box">
          <div className="telemetry-box-top">
            <div className="telemetry-item">
              <span className="telemetry-dot-online" />
              <span>FORENSICS RUNTIME</span>
            </div>
            <span className="telemetry-latency">~120ms</span>
          </div>
          <div className="telemetry-waveform" aria-hidden="true">
            <span className="wave-bar bar-1" />
            <span className="wave-bar bar-2" />
            <span className="wave-bar bar-3" />
            <span className="wave-bar bar-4" />
            <span className="wave-bar bar-5" />
            <span className="wave-bar bar-6" />
            <span className="wave-bar bar-7" />
            <span className="wave-bar bar-8" />
          </div>
          <div className="telemetry-footer-specs">
            <span>ONNX FP16</span>
            <span>·</span>
            <span>AES-256</span>
            <span>·</span>
            <span>EPHEMERAL RAM</span>
          </div>
        </div>

        {/* User Account Footer Card */}
        <div className={`sidebar-bottom${admin ? " admin-sidebar-footer" : ""}`}>
          <div className="avatar-ring">
            <span className="avatar">
              {user.display_name.slice(0, 1).toUpperCase()}
            </span>
            <span className="avatar-status-dot" aria-hidden="true" />
          </div>
          <div className="user-summary">
            <div className="user-name-row">
              <strong title={user.display_name}>{user.display_name}</strong>
              <span className="user-role-tag">{user.role === "admin" ? "ADMIN" : "ANALYST"}</span>
            </div>
            <small title={user.email}>{user.email}</small>
          </div>
          <Tooltip label={admin ? "Sign out of administrator session" : "Sign out of workspace"}>
            <button
              className="sidebar-logout-btn"
              onClick={signOut}
              aria-label="Sign out"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
            </button>
          </Tooltip>
        </div>
      </aside>

      {/* Main Workspace Area */}
      <main className="app-main">
        <header className="app-topline">
          <div className="topline-left">
            <button
              type="button"
              className="mobile-sidebar-toggle"
              onClick={() => setMobileNavOpen(true)}
              aria-label="Open navigation menu"
            >
              <span />
              <span />
              <span />
            </button>
            <div className="topline-breadcrumbs">
              <span className="topline-shield-tag">CGS DEEPFAKE SHIELD</span>
              <span className="breadcrumb-separator">/</span>
              <span className="topline-section-name">
                {pathname === "/app"
                  ? "Dashboard"
                  : pathname === "/app/analyze"
                  ? "Inspection Studio"
                  : pathname === "/app/history"
                  ? "Inspection Ledger"
                  : pathname === "/app/settings"
                  ? "Account Settings"
                  : pathname?.startsWith("/admin")
                  ? "Control Plane & Operations Console"
                  : "Workspace"}
              </span>
            </div>
          </div>

          <div className="topline-actions">
            <span className="privacy-chip">
              <i aria-hidden="true" /> Encrypted Workspace
            </span>
            <ThemeToggle />
          </div>
        </header>

        <div className="app-content-body">
          {children}
        </div>
      </main>
    </div>
  );
}
