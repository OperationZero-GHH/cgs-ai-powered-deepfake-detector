import Link from "next/link";
import { Brand } from "@/components/brand";

export default function VerifyEmailPage() {
  return (
    <div className="auth-page">
      <header className="auth-top">
        <Brand light />
      </header>
      <main className="auth-main">
        <section className="auth-card" style={{ textAlign: "center", maxWidth: "28rem", margin: "2rem auto" }}>
          <div style={{ width: "48px", height: "48px", borderRadius: "50%", background: "rgba(132, 204, 22, 0.15)", color: "#4d7c0f", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 1.2rem", fontSize: "1.5rem", fontWeight: "bold" }}>
            ✓
          </div>
          <h1>Account Active</h1>
          <p className="auth-description" style={{ marginBottom: "1.8rem" }}>
            Email verification is no longer required. Your account is active and you can sign in directly to access the forensic suite.
          </p>
          <Link href="/login" className="button button-primary button-wide btn-lime-themed" style={{ display: "inline-flex", justifyContent: "center", width: "100%" }}>
            Sign in to your account →
          </Link>
        </section>
      </main>
      <footer className="auth-footer">
        <span>© {new Date().getFullYear()} CGS DeepFake Shield</span>
      </footer>
    </div>
  );
}
