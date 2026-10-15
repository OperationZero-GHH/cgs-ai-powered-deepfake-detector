import { Footer, Header } from "@/components/brand";

export default function Loading() {
  return (
    <>
      <Header />
      <main className="page-loading" aria-busy="true" aria-label="Loading page">
        <div className="container page-loading__inner">
          <div className="page-loading__copy">
            <div className="skeleton skeleton-kicker" />
            <div className="skeleton skeleton-title" />
            <div className="skeleton skeleton-title skeleton-title--short" />
            <div className="skeleton skeleton-copy" />
            <div className="skeleton skeleton-copy skeleton-copy--short" />
            <div className="skeleton-actions"><div className="skeleton skeleton-button" /><div className="skeleton skeleton-button skeleton-button--secondary" /></div>
          </div>
          <div className="skeleton-report">
            <div className="skeleton skeleton-report__heading" />
            <div className="skeleton skeleton-report__image" />
            <div className="skeleton skeleton-report__line" />
            <div className="skeleton skeleton-report__line skeleton-report__line--short" />
          </div>
          <div className="skeleton-cards"><div className="skeleton skeleton-card" /><div className="skeleton skeleton-card" /><div className="skeleton skeleton-card" /></div>
        </div>
      </main>
      <Footer />
    </>
  );
}