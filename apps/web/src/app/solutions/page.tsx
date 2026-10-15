import type { Metadata } from "next";
import Link from "next/link";
import { Footer, Header } from "@/components/brand";
import { TestimonialsCarousel } from "@/components/testimonials-carousel";

export const metadata: Metadata = { title: "Solutions" };

const stages = [
  ["01", "Validate the file", "Check supported formats, bounded decoding, dimensions, and a SHA-256 integrity reference."],
  ["02", "Review distinct signals", "Keep file metadata and provenance clues distinct from AI-generation or manipulation analysis."],
  ["03", "Decide with context", "Use the report as one input. Unavailable methods and uncertainty stay visible throughout."],
];

export default function SolutionsPage() {
  return (
    <>
      <Header />
      <main id="main-content" className="route-page solutions-page">
        <section className="container route-intro">
          <span className="eyebrow">Solutions</span>
          <h1>A careful workflow for image evidence.</h1>
          <p>Inspect what can be observed, keep separate questions separate, and give reviewers enough context to make their own judgment.</p>
          <div className="hero-actions">
            <Link className="button button-primary" href="/sign-up">Start an inspection <span aria-hidden="true">→</span></Link>
            <Link className="button button-secondary" href="/technology">See the method</Link>
          </div>
        </section>
        <section className="container solution-stages" aria-label="Review workflow">
          {stages.map(([number, title, description]) => (
            <article className="solution-stage" key={number}>
              <span>{number}</span><h2>{title}</h2><p>{description}</p>
            </article>
          ))}
        </section>
        <section className="solutions-limit container">
          <div><span className="section-kicker">Designed for responsible review</span><h2>Evidence in proportion.<br />No automated verdict.</h2></div>
          <p>The current build supports file checks, hashing, dimensions, limited metadata observations, and private reports. AI classification, manipulation detection, and provenance verification are not configured.</p>
        </section>
        <section id="testimonials" className="testimonials-section">
          <div className="container testimonials-layout">
            <div className="testimonials-heading">
              <span className="eyebrow">Testimonials</span>
              <h2>Clarity matters at every step.</h2>
              <p>Feedback belongs alongside the evidence, with its source and context intact.</p>
            </div>
            <TestimonialsCarousel />
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}