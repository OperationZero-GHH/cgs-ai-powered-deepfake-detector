"use client";

import { useEffect, type ReactNode } from "react";
import { MotionConfig } from "motion/react";

export function MotionProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    // Intercept noisy Chrome extension runtime timeouts to prevent dev overlay disruptions
    const handleRejection = (event: PromiseRejectionEvent) => {
      const reason = event?.reason;
      const str = String(reason?.message || reason?.stack || reason || "");
      if (
        str.includes("chrome-extension://") ||
        str.includes("chrome: call method") ||
        str.includes("timed out")
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    };

    const handleError = (event: ErrorEvent) => {
      const filename = event?.filename || "";
      const message = String(event?.message || "");
      if (
        filename.includes("chrome-extension://") ||
        message.includes("chrome: call method")
      ) {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    };

    window.addEventListener("unhandledrejection", handleRejection, true);
    window.addEventListener("error", handleError, true);

    return () => {
      window.removeEventListener("unhandledrejection", handleRejection, true);
      window.removeEventListener("error", handleError, true);
    };
  }, []);

  return <MotionConfig reducedMotion="user">{children}</MotionConfig>;
}
