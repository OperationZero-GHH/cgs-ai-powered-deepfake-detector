# Model Supply Chain & Specifications

This document defines the cryptographic, architectural, and operational specifications for all machine learning models deployed within CGS DeepFake Shield.

---

## 1. Supply-Chain Governance & Rules

All models in CGS DeepFake Shield are treated as third-party, untrusted dependencies subject to the following non-negotiable rules:

1. **Pinned Revisions:** Every model is pinned to an immutable, full 40-character Git commit hash. The `main` branch or floating tags are never used.
2. **Zero Remote Code (`trust_remote_code=False`):** `trust_remote_code=True` is strictly prohibited across all loaders, pipelines, and workers. Custom architectures are fully reviewed, vendored, and verified locally.
3. **Safe Deserialization Only:** Arbitrary `pickle.load` or unsafe `torch.load` calls are forbidden. Models must provide Hugging Face `.safetensors` format or be loaded exclusively via `torch.load(..., weights_only=True)`.
4. **Cryptographic Integrity (`models.lock.json`):** Every model weight file, config, and preprocessor definition is hashed with SHA-256 and locked in `models.lock.json`. Workers verify SHA-256 on startup and refuse to start if any file is missing, altered, or truncated.
5. **Offline Airgap:** Production inference workers run with `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`. Models are downloaded during the build stage and run completely offline with no network egress.
6. **Probabilistic Outputs & Normalized Scale:** All image and audio models produce normalized `p_fake` scores in the interval `[0.0, 1.0]`. The platform strictly rejects binary truth claims ("100% fake" or "definitely real").

---

## 2. Image Detection Models

### 2.1 `dima806/deepfake_vs_real_image_detection`
- **Hugging Face Repo:** [`dima806/deepfake_vs_real_image_detection`](https://huggingface.co/dima806/deepfake_vs_real_image_detection)
- **Pinned Commit Hash:** `29e4cf9efc543845610045f6ba7e88e5cf9d9301`
- **Architecture:** Vision Transformer (`google/vit-base-patch16-224-in21k` backbone fine-tuned for binary classification)
- **File Format:** SafeTensors (`model.safetensors`, 343,223,968 bytes)
- **SHA-256 Digest:** `b38e7d3de2be44b224cb4cffe881a0c4b75f7283c5d4a2017fbadd58bd41fdef`
- **Input Dimensions:** 3 × 224 × 224 pixels
- **Preprocessing Pipeline:**
  1. RGB conversion and EXIF transpose normalization.
  2. Bilinear resize to 224×224.
  3. ImageNet normalization: Mean `[0.485, 0.456, 0.406]`, Std `[0.229, 0.224, 0.225]`.
- **Label Mapping (`id2label`):**
  - Index `0`: `Real`
  - Index `1`: `Fake`
  - Normalized mapping: `p_fake = softmax(logits)[1]`
- **License:** Apache 2.0 (commercial and open use permitted)
- **Known Limitations:** Concept drift on models released post-2024; reduced sensitivity on non-facial synthetic textures; vulnerability to extreme adversarial compression.

---

### 2.2 `prithivMLmods/Deep-Fake-Detector-v2-Model`
- **Hugging Face Repo:** [`prithivMLmods/Deep-Fake-Detector-v2-Model`](https://huggingface.co/prithivMLmods/Deep-Fake-Detector-v2-Model)
- **Pinned Commit Hash:** `3a99ae26f52c7ac7c3a53103b6cf3a8b617f7093`
- **Architecture:** Vision Transformer (`google/vit-base-patch16-224-in21k` fine-tuned on modern deepfake benchmarks)
- **File Format:** SafeTensors (`model.safetensors`, 343,223,968 bytes)
- **SHA-256 Digest:** `88ac0939285009e3700cfc9b9a0912b14b092d200ef0df86efe4f2cf190ea4de`
- **Input Dimensions:** 3 × 224 × 224 pixels
- **Preprocessing Pipeline:**
  1. RGB conversion and EXIF transpose.
  2. Resize and crop to 224×224.
  3. Feature normalization via ViT ImageProcessor standards.
- **Label Mapping (`id2label`):**
  - Index `0`: `Realism`
  - Index `1`: `Deepfake`
  - Normalized mapping: `p_fake = softmax(logits)[1]`
- **License:** Apache 2.0 (commercial and open use permitted)
- **Known Limitations:** Trained predominantly on frontal face crops; lower confidence on wide-angle scenery and AI-generated text/watermarks.

---

### 2.3 `Harshasnade/Deepfake_Detection_System_V1` (DeepGuard Hybrid)
- **Hugging Face Repo:** [`Harshasnade/Deepfake_Detection_System_V1`](https://huggingface.co/Harshasnade/Deepfake_Detection_System_V1)
- **Pinned Commit Hash:** `14d286569e5fd1deab4def3a2d8af97aff442007`
- **Architecture:** Multi-Branch Hybrid:
  1. **Spatial Branch:** EfficientNetV2-S (1280-d features)
  2. **Frequency Branch:** 2D FFT Log-Magnitude Spectrum CNN (128-d features)
  3. **Patch Anomaly Branch:** 4×4 grid patch encoder with max-pooling (64-d features)
  4. **Global Context Branch:** Swin Transformer V2-T (768-d features)
  5. **Fusion Head:** Linear(2240 -> 512) -> BatchNorm1d -> ReLU -> Dropout(0.5) -> Linear(512 -> 1)
- **File Format:** SafeTensors (`best_model.safetensors`, 202,457,588 bytes)
- **SHA-256 Digest:** `a58fd840e8ebab964a3021acb9e365fe445a86dbcb8af93d808f68eb3a254ad4`
- **Input Dimensions:** 3 × 256 × 256 pixels
- **Preprocessing Pipeline:**
  1. RGB conversion.
  2. Resize to 256×256.
  3. FFT log-magnitude extraction for frequency branch.
  4. 64×64 patch unfolding for patch branch.
- **Output:** Raw scalar logit -> `p_fake = torch.sigmoid(logit)`
- **License Status:** **Unspecified in upstream repository.**
- **Supply-Chain Decision:** Per Section 2 Rule 7 & 8: The architecture has been completely vendored, reviewed, and implemented locally in `app/adapters/harshasnade.py` with zero reliance on remote code. Because the upstream license is unspecified, the model is **disabled by default** behind the configuration flag `ENABLE_HARSHASNADE_MODEL=false`. When disabled, the ensemble runs gracefully on the remaining verified models.

---

### 2.4 Existing Legacy Model: `Thermostatic/community-forensics-low-quality-detector-2026-08`
- **Format:** Verified ONNX FP16 (`community_forensics_low_quality_fp16.onnx`, 43,778,110 bytes)
- **SHA-256 Digest:** `88ca8e90e5ab33e6e13887124614e14ba96d7c8cc9ecb21505b63cdc6549ff17`
- **Architecture:** Low-quality spatial CNN + 2D FFT magnitude spectrum analysis
- **Role:** Fallback spatial validator for low-resolution/high-compression inputs.

---

## 3. Audio Deepfake Detection Models

### 3.1 Model Evaluation & Comparison Matrix
Three candidate open-source models for audio deepfake and speech anti-spoofing detection were evaluated against our criteria:

| Candidate | Architecture | Training Data | SafeTensors Available | Zero Remote Code | Upstream License | Compression Resilience | Selection Outcome |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`Vansh180/deepfake-audio-wav2vec2`** | Wav2Vec2 (`facebook/wav2vec2-base`) | ASVspoof 2021 PA | **Yes** (`model.safetensors`) | **Yes** (Standard Hugging Face) | Apache 2.0 | **High** (Resampled 16 kHz PCM) | **SELECTED** |
| `garystafford/wav2vec2-deepfake-voice-detector` | Wav2Vec2 | Speech Synthesis subsets | No (PyTorch bin) | Yes | MIT | Moderate | Alternate |
| `MelodyMachine/Deepfake-audio-detection-V2` | Audio Spectrogram Transformer | Custom TTS benchmarks | Yes | Requires custom wrapper | CC-BY-NC 4.0 (Non-commercial) | Low | Rejected (License conflict) |

### 3.2 Selected Model: `Vansh180/deepfake-audio-wav2vec2`
- **Hugging Face Repo:** [`Vansh180/deepfake-audio-wav2vec2`](https://huggingface.co/Vansh180/deepfake-audio-wav2vec2)
- **Pinned Commit Hash:** `e1197e2063deb056b0a6a348f3913d27de7f3d83`
- **Architecture:** Wav2Vec2ForSequenceClassification (`facebook/wav2vec2-base` backbone)
- **File Format:** SafeTensors (`model.safetensors`, 378,302,312 bytes)
- **SHA-256 Digest:** `e6bc501e391e78a52f5ce76f34c726c6b30fe225c0d24a37a55daf284b5b70ec`
- **Audio Processing Pipeline:**
  1. Safe decoding via sandboxed FFmpeg: forced to mono, 16,000 Hz, 16-bit PCM WAV.
  2. Amplitude silence detection (RMS energy threshold).
  3. Windowing: 4.0-second sliding windows with 1.0-second stride.
  4. Per-window feature extraction using `Wav2Vec2FeatureExtractor`.
- **Label Mapping (`id2label`):**
  - Index `0`: `real` (bonafide human speech)
  - Index `1`: `fake` (synthetic / cloned speech)
  - Normalized mapping: `p_fake = softmax(logits)[1]`
- **Aggregation:** Mean score + peak anomaly score + percentage of windows exceeding threshold.
- **License:** Apache 2.0 (commercial and open use permitted)
- **Limitations:** Audio detectors struggle against cutting-edge zero-shot voice cloning (e.g. ElevenLabs v3), heavy acoustic reverb, background music, or files shorter than 2.0 seconds.

---

## 4. Video Inspection Pipeline

Video analysis integrates both spatial and audio dimensions:
1. **Frame Extraction:** Sandboxed FFmpeg uniformly extracts keyframes (default 1 fps, maximum 30 frames).
2. **Spatial Ensemble:** Each extracted frame is evaluated through the image model ensemble.
3. **Temporal Analysis:** Frame sequences are evaluated for temporal cross-frame consistency (ResNeXt50 + LSTM temporal detector).
4. **Audio Extraction:** The audio track is isolated via FFmpeg and screened using the audio deepfake detector.
5. **Combined Verdict:** Aggregated video verdict factors spatial mean, peak frame anomaly, temporal variance, and audio authenticity.

