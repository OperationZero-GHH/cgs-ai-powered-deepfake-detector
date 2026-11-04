"use client";

import { useEffect, useRef, useState } from "react";

export type NeuralScanOverlayProps = {
  mediaType?: "image" | "video" | "audio" | "unknown";
  active?: boolean;
  statusText?: string;
  stageIndex?: number;
  fileName?: string;
  isPending?: boolean;
  dimensions?: { width: number; height: number };
  className?: string;
};

const INSPECTION_STAGES = [
  "STAGE 1/5: Binary Magic Byte & Container Verification",
  "STAGE 2/5: Spatial Feature Tensor Extraction (224×224 FP16)",
  "STAGE 3/5: Multi-Head Self-Attention Transformer Scoring",
  "STAGE 4/5: Multi-Spectral Frequency Domain FFT Analysis",
  "STAGE 5/5: Platt-Scaled Multi-Model Consensus Evaluation",
];

export function NeuralScanOverlay({
  mediaType = "image",
  active = true,
  statusText,
  stageIndex,
  fileName,
  isPending = false,
  dimensions,
  className = "",
}: NeuralScanOverlayProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [currentStage, setCurrentStage] = useState(0);

  // Cycle telemetry stages periodically if pending
  useEffect(() => {
    if (!isPending) return;
    const interval = setInterval(() => {
      setCurrentStage((prev) => (prev + 1) % INSPECTION_STAGES.length);
    }, 2400);
    return () => clearInterval(interval);
  }, [isPending]);

  // Canvas Neural Network Nodes & Synapses Animation
  useEffect(() => {
    if (!active) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let width = (canvas.width = canvas.parentElement?.clientWidth || 400);
    let height = (canvas.height = canvas.parentElement?.clientHeight || 280);

    const handleResize = () => {
      if (!canvas.parentElement) return;
      width = canvas.width = canvas.parentElement.clientWidth;
      height = canvas.height = canvas.parentElement.clientHeight;
    };
    window.addEventListener("resize", handleResize);

    // Build neural layer nodes: 4 layers
    // Layer 0: Input layer (4 nodes)
    // Layer 1: Convolutional / Patch embedding (5 nodes)
    // Layer 2: Self-Attention / LSTM latent (6 nodes)
    // Layer 3: Ensemble head (2 nodes)
    const layerSizes = [4, 5, 6, 2];
    type Node = { x: number; y: number; layer: number; baseRadius: number; pulse: number; phase: number };
    const nodes: Node[] = [];

    const layerSpacingX = width / (layerSizes.length + 1);
    layerSizes.forEach((count, lIdx) => {
      const x = layerSpacingX * (lIdx + 1);
      const spacingY = height / (count + 1);
      for (let i = 0; i < count; i++) {
        nodes.push({
          x,
          y: spacingY * (i + 1),
          layer: lIdx,
          baseRadius: lIdx === 0 || lIdx === 3 ? 3.5 : 2.5,
          pulse: 0,
          phase: Math.random() * Math.PI * 2,
        });
      }
    });

    // Synapses (connections between adjacent layers)
    type Synapse = { from: Node; to: Node; pulsePos: number; speed: number };
    const synapses: Synapse[] = [];
    nodes.forEach((n1) => {
      nodes.forEach((n2) => {
        if (n2.layer === n1.layer + 1 && Math.random() > 0.3) {
          synapses.push({
            from: n1,
            to: n2,
            pulsePos: Math.random(),
            speed: 0.008 + Math.random() * 0.012,
          });
        }
      });
    });

    let time = 0;

    const render = () => {
      time += 0.03;
      ctx.clearRect(0, 0, width, height);

      // Draw synapses
      ctx.lineWidth = 1;
      synapses.forEach((syn) => {
        const grad = ctx.createLinearGradient(syn.from.x, syn.from.y, syn.to.x, syn.to.y);
        grad.addColorStop(0, "rgba(163, 230, 53, 0.12)");
        grad.addColorStop(0.5, "rgba(163, 230, 53, 0.28)");
        grad.addColorStop(1, "rgba(163, 230, 53, 0.12)");
        ctx.strokeStyle = grad;

        ctx.beginPath();
        ctx.moveTo(syn.from.x, syn.from.y);
        ctx.lineTo(syn.to.x, syn.to.y);
        ctx.stroke();

        // Traveling pulse packet
        syn.pulsePos += syn.speed;
        if (syn.pulsePos > 1) syn.pulsePos = 0;
        const px = syn.from.x + (syn.to.x - syn.from.x) * syn.pulsePos;
        const py = syn.from.y + (syn.to.y - syn.from.y) * syn.pulsePos;

        ctx.beginPath();
        ctx.arc(px, py, 1.8, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(190, 242, 100, 0.85)";
        ctx.shadowColor = "#a3e635";
        ctx.shadowBlur = 6;
        ctx.fill();
        ctx.shadowBlur = 0;
      });

      // Draw nodes
      nodes.forEach((node) => {
        const pulse = Math.sin(time * 2 + node.phase) * 0.5 + 0.5;
        const r = node.baseRadius + pulse * 1.5;

        // Outer glow halo
        ctx.beginPath();
        ctx.arc(node.x, node.y, r * 2.2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(163, 230, 53, ${0.1 + pulse * 0.25})`;
        ctx.fill();

        // Core dot
        ctx.beginPath();
        ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
        ctx.fillStyle = "#bef264";
        ctx.shadowColor = "#a3e635";
        ctx.shadowBlur = 8;
        ctx.fill();
        ctx.shadowBlur = 0;
      });

      animId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", handleResize);
    };
  }, [active]);

  if (!active) return null;

  const activeStageText =
    stageIndex !== undefined
      ? INSPECTION_STAGES[stageIndex % INSPECTION_STAGES.length]
      : INSPECTION_STAGES[currentStage];

  return (
    <div
      className={`neural-scan-container ${className}`}
      role="region"
      aria-label="Neural model inspection and scanning overlay"
    >
      {/* 4 Forensic Corner Brackets */}
      <div className="neural-hud-corner top-left" aria-hidden="true" />
      <div className="neural-hud-corner top-right" aria-hidden="true" />
      <div className="neural-hud-corner bottom-left" aria-hidden="true" />
      <div className="neural-hud-corner bottom-right" aria-hidden="true" />

      {/* Top Telemetry Header */}
      <div className="neural-hud-header">
        <span className="neural-hud-status-badge">
          <span className="neural-pulse-dot-lime" aria-hidden="true" />
          {statusText || (isPending ? "SCANNING ASSET TO MODEL" : "NEURAL FORENSIC OVERLAY ACTIVE")}
        </span>
        <span className="font-mono">
          {mediaType.toUpperCase()} INSPECTION · FP16 TENSORS
        </span>
      </div>

      {/* Center Targeting Reticle */}
      <div className="neural-center-reticle" aria-hidden="true" />

      {/* Audio Spectrum Bars (if Audio Asset) */}
      {mediaType === "audio" && (
        <div className="neural-audio-spectrum" aria-hidden="true">
          {Array.from({ length: 24 }).map((_, i) => (
            <div
              key={i}
              className="neural-spectrum-bar"
              style={{
                animationDelay: `${(i * 0.08).toFixed(2)}s`,
                animationDuration: `${0.8 + (i % 5) * 0.2}s`,
              }}
            />
          ))}
        </div>
      )}

      {/* Sweeping Laser Beam */}
      <div className="neural-scan-laser" aria-hidden="true" />

      {/* Canvas for Neural Network Nodes & Synapses */}
      <canvas ref={canvasRef} className="neural-scan-canvas" aria-hidden="true" />

      {/* Bottom Telemetry Footer */}
      <div className="neural-hud-footer">
        <div className="neural-telemetry-stage">
          <span className="neural-stage-label">PIPELINE:</span>
          <span>{activeStageText}</span>
        </div>

        <div className="neural-specs-ticker font-mono">
          <div>
            DIM: <strong>{dimensions ? `${dimensions.width}×${dimensions.height}` : "224×224"}</strong>
          </div>
          <div>
            ENCRYPTED: <strong>AES-256 VAULT</strong>
          </div>
          {fileName && <div title={fileName}>FILE: <strong>{fileName.slice(0, 16)}</strong></div>}
        </div>
      </div>
    </div>
  );
}
