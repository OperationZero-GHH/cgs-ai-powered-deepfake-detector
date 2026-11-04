import type { Metadata } from "next";
import { Footer, Header, NoticeBlock } from "@/components/brand";
import { LongFormPage } from "@/components/long-form-page";

export const metadata: Metadata = { title: "How it works" };

const toc = [
  { id: "file-integrity", label: "File integrity" },
  { id: "multi-model-ensemble", label: "Multi-model image ensemble" },
  { id: "audio-forensics", label: "Audio deepfake detection" },
  { id: "calibration-verdict", label: "Calibration & verdicts" },
  { id: "provenance", label: "Provenance & C2PA" },
  { id: "responsible-use", label: "Responsible use & limits" },
];

export default function HowItWorksPage() {
  return (
    <>
      <Header />
      <LongFormPage
        eyebrow="Method and limits"
        title="Probabilistic multi-model forensics across modalities."
        lede="CGS DeepFake Shield combines independent Vision Transformer image classifiers, self-supervised audio speech representation models, and cryptographic provenance checks into a calibrated forensic assessment."
        notice={
          <NoticeBlock
            eyebrow="Probabilistic screening"
            title="Evidence review, not absolute proof."
            body="Deepfake detection models are probabilistic statistical classifiers. They identify patterns correlated with synthetic generation, but do not guarantee 100% accuracy or provide definitive legal proof."
            tone="policy"
          />
        }
        overviewTitle="Forensic architecture"
        overviewItems={[
          "Images: ViT-Base + ViT-v2 + Hybrid CNN/Transformer",
          "Audio: Wav2Vec2 16 kHz sliding-window anti-spoofing",
          "Video: Keyframe sampling + audio extraction",
          "Verdict: Platt-scaled ensemble consensus",
          "Airgapped: Offline execution, pinned commit hashes",
          "Provenance: C2PA manifest & EXIF verification",
        ]}
        toc={toc}
        prevHref="/"
        prevLabel="Home"
        nextHref="/privacy"
        nextLabel="Privacy"
      >
        <section id="file-integrity">
          <span className="section-kicker">§ 01</span>
          <h2>File integrity and sanitization</h2>
          <p>
            Every upload undergoes strict validation prior to inference. The pipeline verifies magic bytes, enforces
            streaming size limits, and sanitizes images through single-frame decoding and RGB re-encoding to eliminate
            parser exploits, decompression bombs, and polyglot files. Cryptographic SHA-256 digests ensure verifiable chain of custody.
          </p>
        </section>

        <section id="multi-model-ensemble">
          <span className="section-kicker">§ 02</span>
          <h2>Multi-model image detection ensemble</h2>
          <p>
            Single models suffer from narrow dataset bias and blind spots. CGS DeepFake Shield deploys an ensemble of
            multiple diverse architectures loaded with pinned SafeTensors weights:
          </p>
          <ul className="checklist">
            <li><strong>dima806/deepfake_vs_real_image_detection:</strong> Vision Transformer (ViT-Base) trained to identify generative facial artifacts.</li>
            <li><strong>prithivMLmods/Deep-Fake-Detector-v2-Model:</strong> Fine-tuned ViT classifier screening for diffusion and generative AI synthetic signatures.</li>
            <li><strong>Harshasnade/Deepfake_Detection_System_V1:</strong> Multi-branch hybrid evaluating spatial features (EfficientNetV2-S), frequency domain patterns (2D FFT CNN), local patch inconsistencies, and global context (Swin-V2-T).</li>
          </ul>
        </section>

        <section id="audio-forensics">
          <span className="section-kicker">§ 03</span>
          <h2>Audio deepfake and speech anti-spoofing</h2>
          <p>
            Standalone audio recordings and extracted video audio tracks are converted to mono 16 kHz PCM WAV via
            sandboxed FFmpeg workers. The audio pipeline utilizes <strong>Vansh180/deepfake-audio-wav2vec2</strong>,
            evaluating self-supervised acoustic representations across sliding temporal windows:
          </p>
          <ul className="checklist">
            <li>Sliding window evaluation (4–6s overlapping segments) detects transient vocoder anomalies and phase discontinuities.</li>
            <li>Energy and silence filters identify empty or low-signal recordings, marking them as insufficient rather than producing misleading scores.</li>
            <li>Known limitations: Detectors are sensitive to severe lossy compression, acoustic reverberation, and novel zero-shot voice cloning architectures.</li>
          </ul>
        </section>

        <section id="calibration-verdict">
          <span className="section-kicker">§ 04</span>
          <h2>Calibration, agreement, and fallback verdicts</h2>
          <p>
            Raw model probabilities are mapped through Platt scaling calibration. Individual model scores are combined
            into a weighted composite score. To prevent false confidence:
          </p>
          <ul className="checklist">
            <li><strong>Likely Manipulated:</strong> Weighted score ≥ 65% with model standard deviation &lt; 0.35.</li>
            <li><strong>Likely Authentic:</strong> Weighted score ≤ 35% with model standard deviation &lt; 0.35.</li>
            <li><strong>Inconclusive:</strong> Triggered whenever models disagree (std dev ≥ 0.35), fewer than 2 active image models contribute, or the composite score falls in the 35%–65% ambiguity band.</li>
          </ul>
        </section>

        <section id="provenance">
          <span className="section-kicker">§ 05</span>
          <h2>Content credentials and provenance</h2>
          <p>
            Where available, C2PA JUMBF manifests are parsed to verify hardware signing roots and digital editing
            lineage. Missing provenance does not indicate malicious manipulation, as many cameras and web platforms
            strip metadata during upload.
          </p>
        </section>

        <section id="responsible-use">
          <span className="section-kicker">§ 06</span>
          <h2>Responsible use and limitations</h2>
          <p>
            CGS DeepFake Shield reports are evidentiary aids intended to inform human review. Automated forensic scores
            must never serve as the sole determinant for legal proceedings, employment decisions, credit assessments, or
            defamation claims.
          </p>
        </section>
      </LongFormPage>
      <Footer />
    </>
  );
}
