"use client";

import { useEffect, useRef, useState, type ComponentPropsWithoutRef, type FocusEvent, type ChangeEvent } from "react";

type SmoothInputProps = Omit<ComponentPropsWithoutRef<"input">, "onChange" | "onBlur"> & {
  onChange?: (event: ChangeEvent<HTMLInputElement>) => void;
  onBlur?: (event: FocusEvent<HTMLInputElement>) => void;
};

export function SmoothInput({
  className,
  style,
  type = "text",
  value,
  defaultValue = "",
  onChange,
  onBlur,
  onFocus,
  ...props
}: SmoothInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const measureRef = useRef<HTMLSpanElement>(null);
  const [internalValue, setInternalValue] = useState(String(defaultValue));
  const [caret, setCaret] = useState({ x: 0, visible: false });
  const controlled = value !== undefined;
  const currentValue = controlled ? String(value ?? "") : internalValue;

  function updateCaret(input = inputRef.current) {
    const measure = measureRef.current;
    if (!input || !measure || document.activeElement !== input) {
      setCaret((current) => ({ ...current, visible: false }));
      return;
    }

    const start = input.selectionStart ?? currentValue.length;
    const end = input.selectionEnd ?? start;
    const inputStyle = window.getComputedStyle(input);
    const isPassword = input.type === "password";
    const fullText = isPassword ? "•".repeat(input.value.length) : input.value;
    const prefix = isPassword ? "•".repeat(start) : input.value.slice(0, start);
    measure.style.font = `${inputStyle.fontStyle} ${inputStyle.fontWeight} ${inputStyle.fontSize} ${inputStyle.fontFamily}`;
    measure.style.letterSpacing = inputStyle.letterSpacing;
    measure.style.fontFeatureSettings = inputStyle.fontFeatureSettings;
    measure.textContent = fullText;
    const fullTextWidth = measure.getBoundingClientRect().width;
    measure.textContent = prefix;
    const prefixWidth = measure.getBoundingClientRect().width;

    const paddingLeft = Number.parseFloat(inputStyle.paddingLeft) || 0;
    const paddingRight = Number.parseFloat(inputStyle.paddingRight) || 0;
    const contentWidth = input.clientWidth - input.clientLeft * 2 - paddingLeft - paddingRight;
    const alignmentOffset = inputStyle.textAlign === "center"
      ? (contentWidth - fullTextWidth) / 2
      : inputStyle.textAlign === "right" || inputStyle.textAlign === "end"
        ? contentWidth - fullTextWidth
        : 0;
    const wrapperLeft = input.parentElement?.getBoundingClientRect().left ?? input.getBoundingClientRect().left;
    const x = input.getBoundingClientRect().left - wrapperLeft + input.clientLeft + paddingLeft + Math.max(0, alignmentOffset) + prefixWidth - input.scrollLeft;
    setCaret({ x, visible: start === end });
  }

  useEffect(() => {
    updateCaret();
  }, [currentValue, type]);

  useEffect(() => {
    const input = inputRef.current;
    if (!input) return;

    const sync = () => updateCaret(input);
    const selectionChanged = () => {
      if (document.activeElement === input) requestAnimationFrame(sync);
    };

    document.addEventListener("selectionchange", selectionChanged);
    window.addEventListener("resize", sync);
    document.fonts.addEventListener("loadingdone", sync);
    return () => {
      document.removeEventListener("selectionchange", selectionChanged);
      window.removeEventListener("resize", sync);
      document.fonts.removeEventListener("loadingdone", sync);
    };
  }, []);

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    if (!controlled) setInternalValue(event.target.value);
    onChange?.(event);
    const input = event.currentTarget;
    requestAnimationFrame(() => updateCaret(input));
  }

  return (
    <span className="smooth-input-wrap">
      <input
        {...props}
        ref={inputRef}
        type={type}
        className={className}
        style={{ ...style, caretColor: "transparent" }}
        value={currentValue}
        onChange={handleChange}
        onFocus={(event) => {
          onFocus?.(event);
          const input = event.currentTarget;
          requestAnimationFrame(() => updateCaret(input));
        }}
        onBlur={(event) => {
          setCaret((current) => ({ ...current, visible: false }));
          onBlur?.(event);
        }}
        onClick={(event) => updateCaret(event.currentTarget)}
        onKeyUp={(event) => updateCaret(event.currentTarget)}
        onScroll={(event) => updateCaret(event.currentTarget)}
      />
      <span ref={measureRef} className="smooth-input-measure" aria-hidden="true" />
      <span
        className="smooth-input-caret"
        aria-hidden="true"
        style={{ transform: `translate(${caret.x}px, -50%)`, opacity: caret.visible ? 1 : 0 }}
      />
    </span>
  );
}
