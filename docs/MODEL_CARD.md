# Synthetic-image screening model card

Checked 2026-10-14. This describes the model used by the local detector adapter, not a model trained or independently validated by CGS DeepFake Shield.

## Model identity

- Model: `Thermostatic/community-forensics-low-quality-detector-2026-08`
- Task: whole-image AI-generated image screening (binary real / AI-generated training task).
- Artifact: `community_forensics_low_quality_fp16.onnx`.
- Artifact size: 43,778,110 bytes.
- Artifact SHA-256: `88ca8e90e5ab33e6e13887124614e14ba96d7c8cc9ecb21505b63cdc6549ff17`.
- License: MIT, according to the model release. Source-data licenses remain specific to each dataset.
- Lineage: independently fine-tuned release based on `OwensLab/commfor-model-384`; it is not an official OwensLab release.
- Runtime: ONNX Runtime CPU provider. The application downloads the ONNX file from the model repository on first launch and refuses to load it if size or SHA-256 differs. It does not execute model-repository Python code or load pickle weights.

## Intended use

Use as one local triage signal for a complete image. It is not proof of authorship, provenance, truth, or malicious intent. Do not use it as the sole basis for an accusation, moderation sanction, employment decision, or legal conclusion.

This is not a face-swap, video, localized-editing, or manipulation-localization detector. A lower score is not proof that an image is natural or unedited. Those capabilities remain explicitly unavailable.

## Preprocessing and output

1. Apply EXIF orientation, convert to RGB, resize the short edge to 440 pixels, and center-crop to 384 × 384.
2. Convert to float32 in `[0,1]`, then normalize channels with ImageNet mean `[0.485, 0.456, 0.406]` and standard deviation `[0.229, 0.224, 0.225]`.
3. Run the single-image ONNX graph on CPU to obtain one raw logit `x`.
4. Compute the published calibration mapping `sigmoid(0.6352260751077209 × x − 0.2643220522904507)`.
5. Apply the published screening threshold `0.65`. The application calls a score at or above this threshold an “AI-generated signal”; a lower score is reported as “No strong AI-generated signal,” while the overall assessment remains inconclusive.

The output is stored as a **calibrated screening score**, not a population probability. Its calibrator was fit on a class-balanced development set, so it does not account for the prevalence of AI-generated images in a particular population. No confidence interval is produced by this app.

## Evaluation reported by the model author

The author reports the following on a 3,912-image group-disjoint development/calibration set. These are the author's results; CGS DeepFake Shield has not independently reproduced them.

| Evaluation view | Balanced accuracy | Fake recall | Real specificity |
|---|---:|---:|---:|
| Clean | 0.9530 | 0.9549 | 0.9511 |
| Web-laundered | 0.9359 | 0.9020 | 0.9697 |
| Hard-degraded | 0.8982 | 0.8543 | 0.9420 |
| Low-quality aggregate | 0.7584 | 0.5612 | — |

The repository states that its locked competition test was not opened. Results are development evidence, not an untouched test estimate.

## Known weaknesses and limits

- The author's 33-condition red-team report is marked `valid: false`. A composite with 5% synthetic foreground reached balanced accuracy 0.5080 and fake recall 0.0492. The model is whole-image only and can miss a small manipulated region.
- The per-image worst-of-attacks fake recall is reported as 0.0026; extreme laundering can defeat the classifier.
- At 96-pixel JPEG quality 20, reported low-quality fake recall is 0.3914; at 64-pixel multi-hop JPEG/WebP it is 0.2374.
- Positive-only recent-generator diagnostics are small (189 and 90 images); they do not estimate balanced accuracy or internet-wide performance.
- External physical recapture, platform laundering, and generative laundering families were absent from the author's coverage statement.
- Generators and editing pipelines change. Screenshots, camera recaptures, composites, and unseen models can shift results.
- ONNX FP16 and PyTorch bfloat16 did not produce identical logits in the reported comparison; the author reports 99.7699% threshold agreement over 11,736 predictions.
- No claim is made that the screening score is calibrated for this app's user population or current base rate.

## Failure behavior

- If the dependency or model file is missing, the detector returns `not_configured` and a null score.
- If checksum/size validation or inference fails, the detector returns a safe failure status and no score. Metadata and C2PA scanning can still complete.
- The worker persists the model identity, score semantics, threshold policy, and inference duration with the report.
- E2E tests use a deterministic fixture explicitly marked `test_only`; provider configuration rejects it outside `APP_ENV=test` or `APP_ENV=e2e`.

## Sources

- [Model repository and complete model card](https://huggingface.co/Thermostatic/community-forensics-low-quality-detector-2026-08)
- [Community Forensics paper](https://arxiv.org/abs/2411.04125)
- [Official Hugging Face Transformers image-classification documentation](https://huggingface.co/docs/transformers/main_classes/pipelines)
