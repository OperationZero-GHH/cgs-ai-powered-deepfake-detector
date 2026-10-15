import type { Metadata } from "next";
import { Footer, Header, NoticeBlock } from "@/components/brand";
import { LongFormPage } from "@/components/long-form-page";

export const metadata: Metadata = { title: "Terms" };

const toc = [
  { id: "service-scope", label: "Service scope" },
  { id: "your-uploads", label: "Your uploads" },
  { id: "high-impact-decisions", label: "High-impact decisions" },
  { id: "availability", label: "Availability and changes" },
];

export default function TermsPage() {
  return (
    <>
      <Header />
      <LongFormPage
        eyebrow="Terms of service"
        title="Use reports as investigative indicators."
        lede="This service is a development tool for file-scoped metadata analysis and evidence review. It should be treated as a technical aid, not a definitive authority on image authenticity or depicted events."
        notice={
          <NoticeBlock
            eyebrow="Starter terms"
            title="Have qualified counsel review these terms before any public launch."
            body="These terms are for development use and are not a final launch-ready legal framework."
            tone="warning"
          />
        }
        overviewTitle="In plain language"
        overviewItems={[
          "Reports are indicators, not proof.",
          "You are responsible for what you upload and how you interpret it.",
          "Do not use this service as the sole basis for high-impact decisions about a person.",
        ]}
        toc={toc}
        prevHref="/privacy"
        prevLabel="Privacy"
        nextHref="/"
        nextLabel="Home"
      >
        <section id="service-scope">
          <span className="section-kicker">§ 01</span>
          <h2>Service scope</h2>
          <p>
            CGS DeepFake Shield provides image file integrity and metadata observations. The current MVP does not provide
            an AI-generated image verdict, face recognition, legal certification, or a guarantee that an image or depicted
            event is authentic.
          </p>
          <ul className="checklist">
            <li>AI-generated image verdict: not provided</li>
            <li>Face recognition: not provided</li>
            <li>Legal certification: not provided</li>
            <li>Authenticity guarantee: not provided</li>
          </ul>
        </section>

        <section id="your-uploads">
          <span className="section-kicker">§ 02</span>
          <h2>Your uploads</h2>
          <p>
            Only upload files you are permitted to use. You are responsible for the lawful handling and interpretation of
            any image and report. Reports are probabilistic or incomplete technical evidence and should be reviewed in
            context.
          </p>
        </section>

        <section id="high-impact-decisions">
          <span className="section-kicker">§ 03</span>
          <h2>High-impact decisions</h2>
          <div className="notice notice--warning">
            <div className="notice__icon" aria-hidden="true">
              !
            </div>
            <div>
              <p className="notice__eyebrow">Warning</p>
              <h3>Do not use this service as the sole basis for high-impact decisions.</h3>
              <p>Do not use this service as the sole basis for legal, employment, medical, financial, or other high-impact decisions about a person.</p>
            </div>
          </div>
        </section>

        <section id="availability">
          <span className="section-kicker">§ 04</span>
          <h2>Availability and changes</h2>
          <p>
            This development service may be incomplete and may change. A production operator must add support,
            jurisdiction, dispute, security incident, and service-specific terms before launch.
          </p>
        </section>
      </LongFormPage>
      <Footer />
    </>
  );
}
