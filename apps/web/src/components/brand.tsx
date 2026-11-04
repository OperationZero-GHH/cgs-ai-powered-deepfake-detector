"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import Image from "next/image";
import { AnimatePresence, motion } from "motion/react";

export function Mark({ small = false }: { small?: boolean }) {
  return (
    <span className={`brand-mark${small ? " brand-mark-small" : ""}`} aria-hidden="true">
      <Image src="/cgs-logo.png" alt="" width={small ? 30 : 42} height={small ? 30 : 42} />
    </span>
  );
}

export function Brand({ light = false }: { light?: boolean }) {
  return (
    <Link href="/" className={`brand${light ? " brand-light" : ""}`} aria-label="CGS DeepFake Shield home">
      <Mark />
      <span className="brand-wordmark">
        <strong>CGS</strong>
        <small>DEEPFAKE SHIELD</small>
      </span>
    </Link>
  );
}

export function StatusChip({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "inspected" | "caution" | "demo" | "inconclusive" | "not-configured" | "unavailable" }) {
  return (
    <span className={`status-chip status-chip--${tone}`}>
      <span className="status-dot" aria-hidden="true" />
      {children}
    </span>
  );
}

export function FactRow({ label, value, chip }: { label: string; value: string; chip?: ReactNode }) {
  return (
    <div className="fact-row">
      <span className="fact-row__label">{label}</span>
      <span className="fact-row__leader" aria-hidden="true" />
      <span className="fact-row__value">
        {chip ?? value}
      </span>
    </div>
  );
}

export function NoticeBlock({
  eyebrow,
  title,
  body,
  tone = "info",
}: {
  eyebrow: string;
  title: string;
  body: string;
  tone?: "info" | "warning" | "policy";
}) {
  return (
    <div className={`notice notice--${tone}`}>
      <div className="notice__icon" aria-hidden="true">
        {tone === "warning" ? "!" : "i"}
      </div>
      <div>
        <p className="notice__eyebrow">{eyebrow}</p>
        <h3>{title}</h3>
        <p>{body}</p>
      </div>
    </div>
  );
}

export function Header() {
  const pathname = usePathname();
  const [activeHref, setActiveHref] = useState(pathname);
  const [scrolled, setScrolled] = useState(false);
  const [progress, setProgress] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const menuCloseTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setActiveHref(pathname);
  }, [pathname]);

  const isLinkActive = (href: string) => {
    if (activeHref === href) return true;
    if (href === "/" && pathname === "/") return true;
    if (href !== "/" && (pathname === href || pathname.startsWith(href + "/"))) return true;
    return false;
  };

  function openMenu() {
    if (menuCloseTimer.current) clearTimeout(menuCloseTimer.current);
    menuCloseTimer.current = null;
    setMenuOpen(true);
  }

  function scheduleMenuClose() {
    if (menuCloseTimer.current) clearTimeout(menuCloseTimer.current);
    menuCloseTimer.current = setTimeout(() => setMenuOpen(false), 450);
  }

  useEffect(() => {
    const onScroll = () => {
      const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
      const nextProgress = maxScroll > 0 ? (window.scrollY / maxScroll) * 100 : 0;
      setProgress(Math.min(100, Math.max(0, nextProgress)));
      setScrolled(window.scrollY > 10);
    };

    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    setMenuOpen(false);
    setMobileMenuOpen(false);
    if (menuCloseTimer.current) clearTimeout(menuCloseTimer.current);
    menuCloseTimer.current = null;
  }, [pathname]);

  useEffect(() => {
    if (!mobileMenuOpen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = previousOverflow; };
  }, [mobileMenuOpen]);

  useEffect(() => () => {
    if (menuCloseTimer.current) clearTimeout(menuCloseTimer.current);
  }, []);

  return (
    <header
      className={scrolled ? "site-header is-scrolled" : "site-header"}
      onMouseLeave={scheduleMenuClose}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setMenuOpen(false);
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape" && mobileMenuOpen) {
          setMobileMenuOpen(false);
          event.currentTarget.querySelector<HTMLButtonElement>(".mobile-menu-toggle")?.focus();
        } else if (event.key === "Escape" && menuOpen) {
          setMenuOpen(false);
          event.currentTarget.querySelector<HTMLButtonElement>(".nav-mega-trigger")?.focus();
        }
      }}
    >
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <div className="container header-inner">
        <Brand />
        <nav className="site-nav" aria-label="Main navigation">
          <Link
            href="/"
            className={isLinkActive("/") ? "is-active" : ""}
            aria-current={isLinkActive("/") ? "page" : undefined}
            onClick={() => setActiveHref("/")}
          >
            Home
          </Link>
          <button
            className="nav-mega-trigger"
            type="button"
            aria-label="Explore site pages"
            aria-controls="site-mega-menu"
            aria-haspopup="true"
            aria-expanded={menuOpen}
            onPointerEnter={(event) => {
              if (event.pointerType === "mouse" || event.pointerType === "pen") openMenu();
            }}
            onPointerLeave={scheduleMenuClose}
            onFocus={(event) => {
              if (event.currentTarget.matches(":focus-visible")) openMenu();
            }}
            onClick={(event) => {
              if ((event.nativeEvent as PointerEvent).pointerType === "touch") {
                if (menuOpen) scheduleMenuClose();
                else openMenu();
              } else {
                openMenu();
              }
            }}
          >
            Explore
          </button>
          <Link
            href="/solutions#testimonials"
            className={isLinkActive("/solutions#testimonials") ? "is-active" : ""}
            aria-current={isLinkActive("/solutions#testimonials") ? "page" : undefined}
            onClick={() => setActiveHref("/solutions#testimonials")}
          >
            Testimonials
          </Link>

          <Link
            href="/about"
            className={isLinkActive("/about") ? "is-active" : ""}
            aria-current={isLinkActive("/about") ? "page" : undefined}
            onClick={() => setActiveHref("/about")}
          >
            About
          </Link>
          <Link
            href="/contact"
            className={isLinkActive("/contact") ? "is-active" : ""}
            aria-current={isLinkActive("/contact") ? "page" : undefined}
            onClick={() => setActiveHref("/contact")}
          >
            Contact
          </Link>
        </nav>
        <div className="header-actions">
          <Link className="button button-primary btn-lime-themed" href="/sign-up">
            Get started <span className="arrow" aria-hidden="true">→</span>
          </Link>
        </div>
        <button
          className={`mobile-menu-toggle${mobileMenuOpen ? " is-open" : ""}`}
          type="button"
          aria-label={mobileMenuOpen ? "Close navigation" : "Open navigation"}
          aria-controls="mobile-site-menu"
          aria-expanded={mobileMenuOpen}
          onClick={() => setMobileMenuOpen((open) => !open)}
        >
          <span />
          <span />
          <span />
        </button>
      </div>
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            className="mobile-menu-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.16 }}
            onClick={() => setMobileMenuOpen(false)}
          >
            <motion.aside
              id="mobile-site-menu"
              className="mobile-menu-drawer"
              role="dialog"
              aria-modal="true"
              aria-label="Site navigation"
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ duration: 0.22, ease: "easeOut" }}
              onClick={(event: React.MouseEvent) => event.stopPropagation()}
            >
              <div className="mobile-menu-head">
                <Brand />
                <button className="mobile-menu-close" type="button" aria-label="Close navigation" onClick={() => setMobileMenuOpen(false)}>×</button>
              </div>
              <nav className="mobile-menu-links" aria-label="Mobile navigation">
                <Link
                  href="/"
                  className={isLinkActive("/") ? "is-active" : ""}
                  aria-current={isLinkActive("/") ? "page" : undefined}
                  onClick={() => { setActiveHref("/"); setMobileMenuOpen(false); }}
                >
                  Home
                </Link>
                <span className="mobile-menu-label">Explore</span>
                <Link
                  href="/solutions"
                  className={isLinkActive("/solutions") ? "is-active" : ""}
                  onClick={() => { setActiveHref("/solutions"); setMobileMenuOpen(false); }}
                >
                  Solutions
                </Link>
                <Link
                  href="/technology"
                  className={isLinkActive("/technology") ? "is-active" : ""}
                  onClick={() => { setActiveHref("/technology"); setMobileMenuOpen(false); }}
                >
                  Technology
                </Link>

                <Link
                  href="/about"
                  className={isLinkActive("/about") ? "is-active" : ""}
                  aria-current={isLinkActive("/about") ? "page" : undefined}
                  onClick={() => { setActiveHref("/about"); setMobileMenuOpen(false); }}
                >
                  About
                </Link>
                <Link
                  href="/contact"
                  className={isLinkActive("/contact") ? "is-active" : ""}
                  aria-current={isLinkActive("/contact") ? "page" : undefined}
                  onClick={() => { setActiveHref("/contact"); setMobileMenuOpen(false); }}
                >
                  Contact
                </Link>
                <Link
                  href="/solutions#testimonials"
                  className={isLinkActive("/solutions#testimonials") ? "is-active" : ""}
                  onClick={() => { setActiveHref("/solutions#testimonials"); setMobileMenuOpen(false); }}
                >
                  Testimonials
                </Link>
                <Link
                  href="/how-it-works"
                  className={isLinkActive("/how-it-works") ? "is-active" : ""}
                  onClick={() => { setActiveHref("/how-it-works"); setMobileMenuOpen(false); }}
                >
                  How it works
                </Link>
                <Link
                  href="/privacy"
                  className={isLinkActive("/privacy") ? "is-active" : ""}
                  onClick={() => { setActiveHref("/privacy"); setMobileMenuOpen(false); }}
                >
                  Privacy
                </Link>
              </nav>
              <div className="mobile-menu-actions">
                <Link className="button button-primary btn-lime-themed" href="/sign-up" onClick={() => setMobileMenuOpen(false)}>
                  Get started <span aria-hidden="true">→</span>
                </Link>
              </div>
            </motion.aside>
          </motion.div>
        )}
      </AnimatePresence>
      <AnimatePresence>
        {menuOpen && (
          <motion.nav
            id="site-mega-menu"
            className="mega-menu"
            aria-label="Explore pages"
            onPointerEnter={openMenu}
            onPointerLeave={scheduleMenuClose}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
          >
            <div className="mega-menu__intro">
              <span className="section-kicker">CGS DeepFake Shield</span>
              <h2>Evidence, in its proper context.</h2>
              <p>Explore the product, methods, and people behind careful image review.</p>
              <Link className="mega-feature" href="/solutions">
                <span className="mega-feature__icon" aria-hidden="true">◈</span>
                <span><strong>Start with solutions</strong><small>See the review workflow</small></span>
                <span aria-hidden="true">↗</span>
              </Link>
            </div>
            <div className="mega-menu__group">
              <p>Product</p>
              <Link href="/solutions">Solutions</Link>
              <Link href="/technology">Technology</Link>

            </div>
            <div className="mega-menu__group">
              <p>Company</p>
              <Link href="/about">About us</Link>
              <Link href="/contact">Contact</Link>
            </div>
            <div className="mega-menu__group">
              <p>Resources</p>
              <Link href="/solutions#testimonials">Testimonials</Link>
              <Link href="/how-it-works">How it works</Link>
              <Link href="/privacy">Privacy</Link>
            </div>
          </motion.nav>
        )}
      </AnimatePresence>
      <div className="header-progress" aria-hidden="true">
        <span style={{ width: `${progress}%` }} />
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="site-footer-modern" role="contentinfo">
      <div className="container">
        {/* Top Status & Integrity Bar */}
        <div className="footer-status-bar">
          <div className="footer-status-left">
            <span className="footer-pulse-dot" aria-hidden="true" />
            <span className="footer-status-text">
              <strong>All Forensic Ensembles Active</strong> · Offline Local Inference · Pinned SHA-256 Checkpoints
            </span>
          </div>
          <div className="footer-status-tags">
            <span className="status-pill">ViT Dual Ensembles</span>
            <span className="status-pill">Wav2Vec2 Audio</span>
            <span className="status-pill">C2PA Manifest Engine</span>
            <span className="status-pill">2D-FFT Spectral Drift</span>
          </div>
        </div>

        {/* Main 5-Column Navigation Grid */}
        <div className="footer-main-grid">
          <div className="footer-brand-pane">
            <div className="footer-brand-wrap">
              <Brand light />
            </div>
            <p className="footer-brand-mission">
              Empowering organizations, newsrooms, and legal researchers with cryptographic provenance,
              frequency-domain drift analytics, and multi-model neural inspection. Evidence for human review, never automated finality.
            </p>
            <div className="footer-guarantees">
              <span className="guarantee-chip">◈ Zero Absolute Claims</span>
              <span className="guarantee-chip">◈ Offline Cryptographic Security</span>
              <span className="guarantee-chip">◈ Open Verification Metrics</span>
            </div>
          </div>

          <div className="footer-col">
            <p className="footer-col-title">Forensic Engine</p>
            <ul className="footer-nav-list">
              <li><Link href="/app/analyze">DeepFake Image Screen</Link></li>
              <li><Link href="/app/analyze">Audio Voice Analysis</Link></li>
              <li><Link href="/app/analyze">Video Frame Sampling</Link></li>
              <li><Link href="/technology">Spectral FFT Residuals</Link></li>
              <li><Link href="/how-it-works">C2PA Metadata Chain</Link></li>
            </ul>
          </div>

          <div className="footer-col">
            <p className="footer-col-title">Use Cases</p>
            <ul className="footer-nav-list">
              <li><Link href="/solutions">Enterprise & Platform Overview</Link></li>
              <li><Link href="/solutions#media">Newsrooms & Media Houses</Link></li>
              <li><Link href="/solutions#legal">Legal & Forensic Evidence</Link></li>
              <li><Link href="/solutions#identity">KYC & Identity Verification</Link></li>
              <li><Link href="/solutions#testimonials">Field Testimonials & Reviews</Link></li>
            </ul>
          </div>

          <div className="footer-col">
            <p className="footer-col-title">Methodology</p>
            <ul className="footer-nav-list">
              <li><Link href="/technology">Multi-Model Architecture</Link></li>
              <li><Link href="/how-it-works">Model Calibration & Bounds</Link></li>
              <li><Link href="/how-it-works">Probabilistic Scoring</Link></li>
              <li><Link href="/about">About CGS Shield Team</Link></li>
              <li><Link href="/contact">Report Discrepancy / Bug</Link></li>
            </ul>
          </div>

          <div className="footer-col">
            <p className="footer-col-title">Access & Legal</p>
            <ul className="footer-nav-list">
              <li><Link href="/login">Account Sign In</Link></li>
              <li><Link href="/sign-up">Register New Account</Link></li>
              <li><Link href="/privacy">Privacy & Data Retention</Link></li>
              <li><Link href="/terms">Terms of Service</Link></li>
              <li><Link href="/contact">Enterprise Contact Desk</Link></li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar with Integrity Notice & Copyright */}
        <div className="footer-bottom-bar">
          <div className="footer-legal-copy">
            <p className="footer-disclaimer">
              <strong>Integrity Notice:</strong> Forensic outputs represent probabilistic indicators calibrated against controlled benchmarks.
              Outputs must be interpreted within verifiable context and do not constitute legal certainty.
            </p>
            <small>© {new Date().getFullYear()} CGS DeepFake Shield. All rights reserved. Designed for truth and accountability.</small>
          </div>
          <div className="footer-actions">
            <a href="#main-content" className="footer-back-to-top" aria-label="Back to top">
              Back to top ↑
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
