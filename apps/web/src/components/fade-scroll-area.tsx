import type { CSSProperties, ReactNode } from "react";

export function FadeScrollArea({
  ariaLabel,
  children,
  className = "",
  maxHeight = "min(62vh, 440px)",
}: {
  ariaLabel: string;
  children: ReactNode;
  className?: string;
  maxHeight?: CSSProperties["maxHeight"];
}) {
  return (
    <div
      className={`fade-scroll-area${className ? ` ${className}` : ""}`}
      role="region"
      aria-label={ariaLabel}
      tabIndex={0}
      style={{ maxHeight }}
    >
      {children}
    </div>
  );
}