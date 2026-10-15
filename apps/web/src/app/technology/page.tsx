import type { Metadata } from "next";
import { Footer, Header } from "@/components/brand";

export const metadata: Metadata = { title: "Technology" };

const methods = [
  ["File validation", "Supported file signatures and safe decoding are checked before inspection."],
  ["Integrity reference", "A SHA-256 hash and image dimensions are recorded for the report."],
  ["Metadata observations", "The current workflow notes EXIF and ICC profile presence; it does not infer authenticity from metadata."],
  ["Model and provenance tasks", "AI-image classification, manipulation localization, and C2PA verification are not configured in this build."],
];

export default function TechnologyPage() {
  return (
    <>
      <Header />
      <main id="main-content" className="route-page technology-page">
        <section className="container route-intro">
          <span className="eyebrow">Technology and method</span>
          <h1>Different questions need different evidence.</h1>
          <p>CGS keeps file integrity, metadata, image classification, manipulation, and provenance separate instead of collapsing them into a certainty score.</p>
        </section>
        <section className="container method-list" aria-label="Inspection methods">
          {methods.map(([title, description], index) => (
            <article className="method-row" key={title}>
              <span className="method-row__number">0{index + 1}</span>
              <h2>{title}</h2>
              <p>{description}</p>
            </article>
          ))}
        </section>
        <p className="container technology-note">A model score is not automatically a probability, and no single detector can establish whether a depicted event is true.</p>
      </main>
      <Footer />
    </>
  );
}