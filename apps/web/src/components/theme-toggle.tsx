"use client";

import { useEffect, useState } from "react";
import { Tooltip } from "@/components/tooltip";

type Theme = "dark" | "light";
const THEME_EVENT = "cgs-theme-change";
let themeTransitionReset: number | undefined;

function readTheme(): Theme {
  try {
    return window.localStorage.getItem("cgs-theme") === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}

function applyTheme(theme: Theme) {
  const root = document.documentElement;
  root.dataset.themeSwitching = "true";
  root.dataset.theme = theme;
  if (themeTransitionReset !== undefined) window.clearTimeout(themeTransitionReset);
  themeTransitionReset = window.setTimeout(() => {
    delete root.dataset.themeSwitching;
    themeTransitionReset = undefined;
  }, 80);
  try {
    window.localStorage.setItem("cgs-theme", theme);
  } catch {
    // The preference still applies for the current page when storage is unavailable.
  }
  window.dispatchEvent(new CustomEvent<Theme>(THEME_EVENT, { detail: theme }));
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    const sync = (event?: Event) => {
      const next = event instanceof CustomEvent && (event.detail === "dark" || event.detail === "light")
        ? event.detail
        : readTheme();
      document.documentElement.dataset.theme = next;
      setTheme(next);
    };
    sync();
    window.addEventListener("storage", sync);
    window.addEventListener(THEME_EVENT, sync);
    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener(THEME_EVENT, sync);
    };
  }, []);

  function toggleTheme() {
    applyTheme(theme === "dark" ? "light" : "dark");
  }

  const nextTheme = theme === "dark" ? "light" : "dark";
  return (
    <Tooltip label={`Switch to ${nextTheme} theme`}>
      <button
        className="theme-toggle"
        type="button"
        aria-label={`Switch to ${nextTheme} theme`}
        aria-pressed={theme === "light"}
        onClick={toggleTheme}
      >
        {theme === "dark" ? (
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.7"/><path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/></svg>
        ) : (
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M20.2 15.1A8.4 8.4 0 0 1 8.9 3.8 8.6 8.6 0 1 0 20.2 15.1Z" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/></svg>
        )}
        <span>{theme === "dark" ? "Dark" : "Light"}</span>
      </button>
    </Tooltip>
  );
}
