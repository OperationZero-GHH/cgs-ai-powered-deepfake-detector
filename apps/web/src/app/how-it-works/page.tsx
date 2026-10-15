import type { Metadata } from "next";
import { Footer, Header, NoticeBlock } from "@/components/brand";
import { LongFormPage } from "@/components/long-form-page";

export const metadata: Metadata = { title: "How it works" };

const toc = [
  { id: "file-integrity", label: "File integrity" },
  { id: "ai-classification", label: "AI classification" },
  { id: "manipulation", label: "Manipulation" },
  { id: "provenance", label: "Provenance" },
  { id: "responsible-use", label: "Responsible use" },
];

export default function HowItWorksPage() {
  return (
    <>
      <Header />
      <LongFormPage
        eyebrow="Method and limits"
        title="Different questions need different evidence."
        lede="CGS DeepFake Shield keeps file integrity, provenance, synthetic-image classification, and manipulation analysis distinct. The local MVP records file facts; validated AI-image and manipulation detectors are not configured."
        notice={
          <NoticeBlock
            eyebrow="Current capability"
            title="Read it as a bounded evidentiary report."
            body="JPEG, PNG, and WebP validation; bounded image decoding; SHA-256; image dimensions; limited metadata-presence observations; private report history. No AI-generated image score or probability is available."
            tone="policy"
          />
        }
        overviewTitle="Current capability"
        overviewItems={[
          "Formats: JPEG, PNG, WebP",
          "Bounded decoding: enabled",
          "Hashing: SHA-256",
          "Metadata: EXIF and ICC presence only",
          "Storage: Private report history",
          "AI score or probability: Not available",
        ]}
        toc={toc}
        prevHref="/"
        prevLabel="Home"
        nextHref="/privacy"
        nextLabel="Privacy"
      >
        <section id="file-integrity">
          <span className="section-kicker">§ 01</span>
          <h2>File integrity and metadata</h2>
          <p>
            The service checks the file signature and decodability, records its dimensions and hash, and notes whether
            EXIF or an ICC profile was present. The preview is normalized for safe display. None of these observations can
            determine whether an image is true, AI-generated, or manipulated.
          </p>
        </section>

        <section id="ai-classification">
          <span className="section-kicker">§ 02</span>
          <h2>AI-generated image classification</h2>
          <p>
            A useful classifier needs a clearly documented model, task-specific evaluation, licensing terms,
            preprocessing rules, operating thresholds, and known weaknesses. A model score is not automatically a
            probability. Until a validated provider and policy are configured, the report explicitly marks the task as
            unavailable and returns an inconclusive overall classification.
          </p>
          <ul className="checklist">
            <li>Documented model and training scope</li>
            <li>Task-specific evaluation and known failure modes</li>
            <li>Explicit operating thresholds and threshold rationale</li>
            <li>Defined preprocessing and input assumptions</li>
            <li>Provider or operator accountability</li>
            <li>Policy for uncertainty, appeals, and limits</li>
          </ul>
        </section>

        <section id="manipulation">
          <span className="section-kicker">§ 03</span>
          <h2>Manipulation and face-swap indicators</h2>
          <p>
            Localized editing and face manipulation are separate tasks. Face presence is not evidence of face swapping,
            and a general synthetic-image detector cannot stand in for a manipulation-localization method. The current
            build does not configure those detectors.
          </p>
        </section>

        <section id="provenance">
          <span className="section-kicker">§ 04</span>
          <h2>Provenance</h2>
          <p>
            C2PA credentials can provide verifiable assertions about content history when a compatible verifier and valid
            credentials are present. This MVP does not include a C2PA verifier. Even valid provenance does not prove the
            truth of the depicted event or scene.
          </p>
        </section>

        <section id="responsible-use">
          <span className="section-kicker">§ 05</span>
          <h2>Responsible use</h2>
          <p>
            Use the report as one investigative input, not legal certification, proof of identity, or the sole basis for
            employment, financial, medical, or other high-impact decisions about a person.
          </p>
        </section>
      </LongFormPage>
      <Footer />
    </>
  );
}
