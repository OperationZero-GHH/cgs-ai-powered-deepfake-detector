"use client";

import { useState } from "react";
import { Tooltip } from "@/components/tooltip";

const testimonials = [
  {
    quote: "I can see what the system measured, what it could not determine, and where human review still matters.",
    name: "Illustrative reviewer",
    role: "Digital evidence review",
  },
  {
    quote: "Keeping metadata observations separate from model claims makes the report easier to discuss responsibly.",
    name: "Illustrative analyst",
    role: "Trust and safety",
  },
  {
    quote: "The most useful result is sometimes a clear explanation of what remains unknown.",
    name: "Illustrative investigator",
    role: "Media verification",
  },
];

export function TestimonialsCarousel() {
  const [active, setActive] = useState(0);
  const testimonial = testimonials[active];

  function move(offset: number) {
    setActive((current) => (current + offset + testimonials.length) % testimonials.length);
  }

  return (
    <div className="testimonial-carousel" aria-roledescription="carousel" aria-label="Illustrative testimonials">
      <div className="testimonial-carousel__quote" aria-live="polite" aria-atomic="true">
        <span className="testimonial-mark" aria-hidden="true">“</span>
        <blockquote>{testimonial.quote}</blockquote>
        <div className="testimonial-attribution">
          <span className="testimonial-avatar" aria-hidden="true">{String(active + 1).padStart(2, "0")}</span>
          <span><strong>{testimonial.name}</strong><small>{testimonial.role}</small></span>
        </div>
      </div>
      <div className="testimonial-controls">
        <Tooltip label="Previous testimonial"><button type="button" onClick={() => move(-1)} aria-label="Previous testimonial">←</button></Tooltip>
        <div className="testimonial-dots" role="group" aria-label="Choose testimonial">
          {testimonials.map((item, index) => (
            <button
              key={item.name}
              type="button"
              className={index === active ? "is-active" : undefined}
              aria-label={`Show testimonial ${index + 1}`}
              aria-pressed={index === active}
              onClick={() => setActive(index)}
            />
          ))}
        </div>
        <Tooltip label="Next testimonial"><button type="button" onClick={() => move(1)} aria-label="Next testimonial">→</button></Tooltip>
      </div>
      <p className="testimonial-disclaimer">Illustrative sample copy only. Replace with verified, approved customer feedback before publication.</p>
    </div>
  );
}