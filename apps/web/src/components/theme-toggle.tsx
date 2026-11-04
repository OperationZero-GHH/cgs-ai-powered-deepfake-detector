"use client";

import { useEffect } from "react";

export function ThemeToggle() {
  useEffect(() => {
    document.documentElement.dataset.theme = "light";
    try {
      window.localStorage.setItem("cgs-theme", "light");
    } catch {
      // Ignore if localStorage unavailable
    }
  }, []);

  return null;
}
