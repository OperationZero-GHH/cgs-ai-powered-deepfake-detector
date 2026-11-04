/**
 * Type & Magic Byte Verification Engine
 * Validates real binary signatures of uploaded assets to guarantee container integrity,
 * detect format spoofing, and correctly route assets to deepfake neural pipelines.
 */

export type TypeVerificationResult = {
  verified: boolean;
  status: "verified" | "failed" | "unsupported";
  category: "image" | "video" | "audio" | "unknown";
  format: string;
  mimeType: string;
  magicHex: string;
  declaredExtension: string;
  signatureMatch: boolean;
  modelPipeline: string;
  targetModels: string[];
  message: string;
};

export async function verifyAssetType(file: File): Promise<TypeVerificationResult> {
  const extension = (file.name.split(".").pop() || "").toLowerCase();
  
  try {
    const slice = file.slice(0, 64);
    const buffer = await slice.arrayBuffer();
    const bytes = new Uint8Array(buffer);

    // Format magic hex (first 8 bytes)
    const magicHex = Array.from(bytes.slice(0, Math.min(8, bytes.length)))
      .map((b) => b.toString(16).padStart(2, "0").toUpperCase())
      .join(" ");

    // 1. JPEG: FF D8 FF
    if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) {
      const isMatch = ["jpg", "jpeg", "jpe"].includes(extension);
      return {
        verified: true,
        status: "verified",
        category: "image",
        format: "JPEG",
        mimeType: "image/jpeg",
        magicHex,
        declaredExtension: extension,
        signatureMatch: isMatch,
        modelPipeline: "Vision Transformer & Hybrid CNN Ensemble",
        targetModels: [
          "Dima ViT (Vision Transformer)",
          "Prithiv ViT-v2 Classifier",
          "Harshasnade Hybrid (EfficientNetV2 + Swin)",
          "Multi-Spectral FFT Frequency Domain Drift",
        ],
        message: isMatch
          ? "Authentic JPEG container verified."
          : `Valid JPEG container verified (declared as .${extension}).`,
      };
    }

    // 2. PNG: 89 50 4E 47 0D 0A 1A 0A
    if (
      bytes.length >= 8 &&
      bytes[0] === 0x89 &&
      bytes[1] === 0x50 &&
      bytes[2] === 0x4e &&
      bytes[3] === 0x47 &&
      bytes[4] === 0x0d &&
      bytes[5] === 0x0a &&
      bytes[6] === 0x1a &&
      bytes[7] === 0x0a
    ) {
      const isMatch = extension === "png";
      return {
        verified: true,
        status: "verified",
        category: "image",
        format: "PNG",
        mimeType: "image/png",
        magicHex,
        declaredExtension: extension,
        signatureMatch: isMatch,
        modelPipeline: "Vision Transformer & Hybrid CNN Ensemble",
        targetModels: [
          "Dima ViT (Vision Transformer)",
          "Prithiv ViT-v2 Classifier",
          "Harshasnade Hybrid (EfficientNetV2 + Swin)",
          "Multi-Spectral FFT Frequency Domain Drift",
        ],
        message: isMatch
          ? "Authentic PNG container verified."
          : `Valid PNG container verified (declared as .${extension}).`,
      };
    }

    // 3. WebP: RIFF (bytes 0-3) ... WEBP (bytes 8-11)
    if (
      bytes.length >= 12 &&
      bytes[0] === 0x52 &&
      bytes[1] === 0x49 &&
      bytes[2] === 0x46 &&
      bytes[3] === 0x46 &&
      bytes[8] === 0x57 &&
      bytes[9] === 0x45 &&
      bytes[10] === 0x42 &&
      bytes[11] === 0x50
    ) {
      const isMatch = extension === "webp";
      return {
        verified: true,
        status: "verified",
        category: "image",
        format: "WebP",
        mimeType: "image/webp",
        magicHex,
        declaredExtension: extension,
        signatureMatch: isMatch,
        modelPipeline: "Vision Transformer & Hybrid CNN Ensemble",
        targetModels: [
          "Dima ViT (Vision Transformer)",
          "Prithiv ViT-v2 Classifier",
          "Harshasnade Hybrid (EfficientNetV2 + Swin)",
          "Multi-Spectral FFT Frequency Domain Drift",
        ],
        message: isMatch
          ? "Authentic WebP container verified."
          : `Valid WebP container verified (declared as .${extension}).`,
      };
    }

    // 4. WebM / Matroska: 1A 45 DF A3
    if (
      bytes.length >= 4 &&
      bytes[0] === 0x1a &&
      bytes[1] === 0x45 &&
      bytes[2] === 0xdf &&
      bytes[3] === 0xa3
    ) {
      const isMatch = ["webm", "mkv"].includes(extension);
      return {
        verified: true,
        status: "verified",
        category: "video",
        format: "WebM",
        mimeType: "video/webm",
        magicHex,
        declaredExtension: extension,
        signatureMatch: isMatch,
        modelPipeline: "Dual-Layer Spatio-Temporal Video Ensemble",
        targetModels: [
          "Layer 1: Keyframe Spatial ONNX Scoring",
          "Layer 2: ResNext50 + Temporal LSTM Sequence Model",
          "C2PA Provenance Manifest Verification",
        ],
        message: isMatch
          ? "Authentic WebM/MKV video stream verified."
          : `Valid WebM video container verified (declared as .${extension}).`,
      };
    }

    // 5. MP4 / MOV / M4A: ISO BMFF with 'ftyp', 'moov', 'wide', or 'mdat' at offset 4
    if (bytes.length >= 12 && bytes[4] === 0x66 && bytes[5] === 0x74 && bytes[6] === 0x79 && bytes[7] === 0x70) {
      const brand = String.fromCharCode(bytes[8], bytes[9], bytes[10], bytes[11]).trim();
      const isQuickTime = brand === "qt";
      const isM4A = brand === "M4A" || brand === "M4B" || extension === "m4a";

      if (isM4A) {
        return {
          verified: true,
          status: "verified",
          category: "audio",
          format: "M4A",
          mimeType: "audio/mp4",
          magicHex,
          declaredExtension: extension,
          signatureMatch: ["m4a", "mp4", "aac"].includes(extension),
          modelPipeline: "Wav2Vec2 Acoustic Forensics Pipeline",
          targetModels: [
            "Vansh180 Wav2Vec2 Acoustic Classifier",
            "16 kHz Mono PCM Window Analysis",
            "Spectral Phoneme Inconsistency Detector",
          ],
          message: "Authentic M4A/AAC audio container verified.",
        };
      }

      const formatName = isQuickTime ? "MOV" : "MP4";
      const mime = isQuickTime ? "video/quicktime" : "video/mp4";
      const isMatch = ["mp4", "mov", "m4v"].includes(extension);

      return {
        verified: true,
        status: "verified",
        category: "video",
        format: formatName,
        mimeType: mime,
        magicHex,
        declaredExtension: extension,
        signatureMatch: isMatch,
        modelPipeline: "Dual-Layer Spatio-Temporal Video Ensemble",
        targetModels: [
          "Layer 1: Keyframe Spatial ONNX Scoring",
          "Layer 2: ResNext50 + Temporal LSTM Sequence Model",
          "C2PA Provenance Manifest Verification",
        ],
        message: isMatch
          ? `Authentic ${formatName} (Brand: ${brand || "isom"}) video stream verified.`
          : `Valid ${formatName} container verified (declared as .${extension}).`,
      };
    }

    // 6. AVI: RIFF....AVI
    if (
      bytes.length >= 12 &&
      bytes[0] === 0x52 &&
      bytes[1] === 0x49 &&
      bytes[2] === 0x46 &&
      bytes[3] === 0x46 &&
      bytes[8] === 0x41 &&
      bytes[9] === 0x56 &&
      bytes[10] === 0x49 &&
      bytes[11] === 0x20
    ) {
      const isMatch = extension === "avi";
      return {
        verified: true,
        status: "verified",
        category: "video",
        format: "AVI",
        mimeType: "video/x-msvideo",
        magicHex,
        declaredExtension: extension,
        signatureMatch: isMatch,
        modelPipeline: "Dual-Layer Spatio-Temporal Video Ensemble",
        targetModels: [
          "Layer 1: Keyframe Spatial ONNX Scoring",
          "Layer 2: ResNext50 + Temporal LSTM Sequence Model",
        ],
        message: isMatch
          ? "Authentic AVI video container verified."
          : `Valid AVI video container verified (declared as .${extension}).`,
      };
    }

    // 7. WAV: RIFF....WAVE
    if (
      bytes.length >= 12 &&
      bytes[0] === 0x52 &&
      bytes[1] === 0x49 &&
      bytes[2] === 0x46 &&
      bytes[3] === 0x46 &&
      bytes[8] === 0x57 &&
      bytes[9] === 0x41 &&
      bytes[10] === 0x56 &&
      bytes[11] === 0x45
    ) {
      const isMatch = extension === "wav";
      return {
        verified: true,
        status: "verified",
        category: "audio",
        format: "WAV",
        mimeType: "audio/wav",
        magicHex,
        declaredExtension: extension,
        signatureMatch: isMatch,
        modelPipeline: "Wav2Vec2 Acoustic Forensics Pipeline",
        targetModels: [
          "Vansh180 Wav2Vec2 Acoustic Classifier",
          "16 kHz Mono PCM Window Analysis",
          "Spectral Phoneme Inconsistency Detector",
        ],
        message: isMatch
          ? "Authentic WAV PCM audio stream verified."
          : `Valid WAV audio stream verified (declared as .${extension}).`,
      };
    }

    // 8. FLAC: fLaC (66 4C 61 43)
    if (
      bytes.length >= 4 &&
      bytes[0] === 0x66 &&
      bytes[1] === 0x4c &&
      bytes[2] === 0x61 &&
      bytes[3] === 0x43
    ) {
      const isMatch = extension === "flac";
      return {
        verified: true,
        status: "verified",
        category: "audio",
        format: "FLAC",
        mimeType: "audio/flac",
        magicHex,
        declaredExtension: extension,
        signatureMatch: isMatch,
        modelPipeline: "Wav2Vec2 Acoustic Forensics Pipeline",
        targetModels: [
          "Vansh180 Wav2Vec2 Acoustic Classifier",
          "16 kHz Mono PCM Window Analysis",
        ],
        message: isMatch
          ? "Authentic FLAC lossless audio stream verified."
          : `Valid FLAC audio stream verified (declared as .${extension}).`,
      };
    }

    // 9. OGG: OggS (4F 67 67 53)
    if (
      bytes.length >= 4 &&
      bytes[0] === 0x4f &&
      bytes[1] === 0x67 &&
      bytes[2] === 0x67 &&
      bytes[3] === 0x53
    ) {
      const isMatch = ["ogg", "oga"].includes(extension);
      return {
        verified: true,
        status: "verified",
        category: "audio",
        format: "OGG",
        mimeType: "audio/ogg",
        magicHex,
        declaredExtension: extension,
        signatureMatch: isMatch,
        modelPipeline: "Wav2Vec2 Acoustic Forensics Pipeline",
        targetModels: [
          "Vansh180 Wav2Vec2 Acoustic Classifier",
          "16 kHz Mono PCM Window Analysis",
        ],
        message: isMatch
          ? "Authentic OGG Vorbis/Opus stream verified."
          : `Valid OGG stream verified (declared as .${extension}).`,
      };
    }

    // 10. MP3: ID3 or sync frame 0xFF with bits 11-13 set
    if (
      (bytes.length >= 3 && bytes[0] === 0x49 && bytes[1] === 0x44 && bytes[2] === 0x33) ||
      (bytes.length >= 2 && bytes[0] === 0xff && (bytes[1] & 0xe0) === 0xe0)
    ) {
      const isMatch = extension === "mp3";
      return {
        verified: true,
        status: "verified",
        category: "audio",
        format: "MP3",
        mimeType: "audio/mpeg",
        magicHex,
        declaredExtension: extension,
        signatureMatch: isMatch,
        modelPipeline: "Wav2Vec2 Acoustic Forensics Pipeline",
        targetModels: [
          "Vansh180 Wav2Vec2 Acoustic Classifier",
          "16 kHz Mono PCM Window Analysis",
        ],
        message: isMatch
          ? "Authentic MPEG Layer-3 audio verified."
          : `Valid MP3 audio verified (declared as .${extension}).`,
      };
    }

    // 11. AAC: ADTS sync word (0xFF 0xF1 or 0xFF 0xF9)
    if (bytes.length >= 2 && bytes[0] === 0xff && (bytes[1] === 0xf1 || bytes[1] === 0xf9)) {
      const isMatch = extension === "aac";
      return {
        verified: true,
        status: "verified",
        category: "audio",
        format: "AAC",
        mimeType: "audio/aac",
        magicHex,
        declaredExtension: extension,
        signatureMatch: isMatch,
        modelPipeline: "Wav2Vec2 Acoustic Forensics Pipeline",
        targetModels: ["Vansh180 Wav2Vec2 Acoustic Classifier"],
        message: "Authentic AAC ADTS audio verified.",
      };
    }

    // Unrecognized or unsupported signature
    return {
      verified: false,
      status: "unsupported",
      category: "unknown",
      format: "UNKNOWN",
      mimeType: file.type || "application/octet-stream",
      magicHex,
      declaredExtension: extension,
      signatureMatch: false,
      modelPipeline: "None",
      targetModels: [],
      message:
        "Binary magic bytes unverified. Upload an authentic JPEG, PNG, WebP, MP4, WebM, MOV, WAV, MP3, FLAC, or OGG file.",
    };
  } catch (error) {
    return {
      verified: false,
      status: "failed",
      category: "unknown",
      format: "ERROR",
      mimeType: file.type || "application/octet-stream",
      magicHex: "",
      declaredExtension: extension,
      signatureMatch: false,
      modelPipeline: "None",
      targetModels: [],
      message: error instanceof Error ? error.message : "Failed to verify asset container signature.",
    };
  }
}

