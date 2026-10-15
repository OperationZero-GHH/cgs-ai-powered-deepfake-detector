import type { Metadata } from "next";
import { Footer, Header, NoticeBlock } from "@/components/brand";
import { LongFormPage } from "@/components/long-form-page";

export const metadata: Metadata = { title: "Privacy" };

const toc = [
  { id: "what-is-stored", label: "What is stored" },
  { id: "why-stored", label: "Why it is stored" },
  { id: "access-and-deletion", label: "Access and deletion" },
  { id: "logs-and-services", label: "Logs and services" },
  { id: "retention", label: "Retention" },
  { id: "cookies", label: "Cookie preferences" },
];

const glanceItems = [
  "Stored privately: original image or video + normalized preview",
  "Not sent to third-party inference providers by this MVP",
  "No required analytics calls; system fonts only",
  "Delete an analysis or account from Settings",
  "Reports stay until deletion or an enabled retention policy",
  "No image contents or full EXIF in local API logs",
];

export default function PrivacyPage() {
  return (
    <>
      <Header />
      <LongFormPage
        eyebrow="Privacy"
        title="Uploaded media stays under your control."
        lede="This page sets out the current MVP privacy posture and the limits of that posture. It is a starter policy for development and not a compliance certification."
        notice={
          <NoticeBlock
            eyebrow="Starter policy"
            title="A privacy and legal review is required before launch."
            body="This page is not a compliance certification and should not be treated as a completed product policy."
            tone="warning"
          />
        }
        overviewTitle="Privacy at a glance"
        overviewItems={glanceItems}
        toc={toc}
        prevHref="/how-it-works"
        prevLabel="How it works"
        nextHref="/terms"
        nextLabel="Terms"
      >
        <section id="what-is-stored">
          <span className="section-kicker">§ 01</span>
          <h2>What is stored</h2>
          <p>
            When you create an account, the service stores your normalized email identity, username, display name,
            optional phone number, password hash, email-verification state, and server-side session
            records. Verification and password-reset tokens are stored as hashes. A guest receives a signed essential
            cookie. For account security, the API stores keyed hashes of network IP addresses; it does not store raw IP
            addresses or device fingerprints. IP-account controls also retain account links and access audit
            records. An unblock request stores the submitted name, email, reason, and reference ID. When you upload an image or video, it stores the original media
            privately, a normalized preview, the original filename as display text, detected format, size, dimensions,
            SHA-256, and limited metadata-presence facts.
          </p>

          <table className="data-table">
            <thead>
              <tr>
                <th>Account data</th>
                <th>Upload data</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Email identity, username, display name, optional phone, password hash, verification state, token digests, session records, hashed IP/account controls</td>
                <td>Original media, preview, filename, format, size, dimensions, SHA-256, limited metadata facts</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section id="why-stored">
          <span className="section-kicker">§ 02</span>
          <h2>Why it is stored</h2>
          <p>
            Media bytes are retained to show your report preview and to support the analysis workflow. The local analysis
            worker uses the media on the server. By this MVP, media bytes are not sent to a third-party inference provider.
            The result is a fallible screening signal, not proof of origin, and this model does not locate edited regions
            or identify face swaps. The worker also reads C2PA Content Credentials when available; a missing C2PA manifest
            does not establish that an image is authentic.
          </p>
        </section>

        <section id="access-and-deletion">
          <span className="section-kicker">§ 03</span>
          <h2>Access and deletion</h2>
          <p>
            Reports and previews are scoped to the signed guest identity or account that created them. You can delete an
            analysis or your account from Settings; the app removes associated local files and database records. This
            does not guarantee removal from backups managed by a future deployment.
          </p>
        </section>

        <section id="logs-and-services">
          <span className="section-kicker">§ 04</span>
          <h2>Logs and external services</h2>
          <p>
            The local API does not log media contents or full EXIF data. Without SMTP, local development writes one-time
            verification/reset links to the API log for QA; production requires an SMTP relay. The frontend makes no
            required analytics calls. A production operator must document hosting, trusted proxies, observability,
            email, storage, or model providers.
          </p>
        </section>

        <section id="retention">
          <span className="section-kicker">§ 05</span>
          <h2>Retention</h2>
          <div className="notice notice--warning">
            <div className="notice__icon" aria-hidden="true">
              !
            </div>
            <div>
              <p className="notice__eyebrow">Retention caution</p>
              <h3>By default, reports remain until deletion.</h3>
              <p>The default UPLOAD_RETENTION_DAYS=0 disables automatic cleanup. Operators may set a positive value to remove terminal reports and stored media after that many days. Processing reports are retained until they finish. Backup deletion follows the deployment’s backup policy.</p>
            </div>
          </div>
        </section>

        <section id="cookies">
          <span className="section-kicker">§ 06</span>
          <h2>Cookies and preferences</h2>
          <p>
            Authentication and guest identity use essential HttpOnly server-side cookies. The current frontend does not configure
            analytics or advertising cookies. Your choice in the cookie banner is stored in this browser's local
            storage; it does not create or enable optional cookies. You can change that preference by clearing this
            browser's site data and responding to the banner again.
          </p>
        </section>
      </LongFormPage>
      <Footer />
    </>
  );
}
