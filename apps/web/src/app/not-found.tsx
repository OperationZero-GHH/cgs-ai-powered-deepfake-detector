import Link from "next/link";
import { Footer, Header } from "@/components/brand";

export default function NotFound() {
  return (
    <>
      <Header />
      <main id="main-content" className="not-found-page">
        <div className="not-found-grid" aria-hidden="true" />
        <section className="not-found-content">
          <span className="not-found-code">404 / NOT FOUND</span>
          <h1>We couldn’t find that page.</h1>
          <p>The address may have changed, or the page may no longer be available. Head home or contact the team for help.</p>
          <div className="not-found-actions">
            <Link className="button button-primary" href="/">Back to home <span aria-hidden="true">→</span></Link>
            <Link className="button button-secondary" href="/contact">Contact support</Link>
          </div>
        </section>
        <div className="not-found-mark" aria-hidden="true">CGS<span> / 404</span></div>
      </main>
      <Footer />
    </>
  );
}