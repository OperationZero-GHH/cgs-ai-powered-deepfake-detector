import type { Metadata } from "next";
import Link from "next/link";
import { Footer, Header } from "@/components/brand";

export const metadata: Metadata = { title: "About us" };

export default function AboutPage() {
  return (
    <>
      <Header />
      <main id="main-content" className="route-page about-page">
        <section className="container route-intro route-intro--wide">
          <span className="eyebrow">About CGS</span>
          <h1>Make image review more careful, not more certain.</h1>
          <p>CGS DeepFake Shield is built around a practical idea: image-analysis tools should show their observations, explain their limits, and leave consequential decisions to people.</p>
        </section>
        <section className="container about-principles">
          <article><span>01 / TRANSPARENCY</span><h2>Show the work.</h2><p>File facts and technical observations stay visible, so a reviewer can understand what was actually checked.</p></article>
          <article><span>02 / HUMILITY</span><h2>Keep uncertainty visible.</h2><p>Unavailable methods are labeled unavailable. Metadata and model signals are not treated as proof.</p></article>
          <article><span>03 / RESPONSIBILITY</span><h2>People make the call.</h2><p>Reports support an investigation; they do not replace context, expertise, or fair human judgment.</p></article>
        </section>
        <section className="container about-cta"><p>Want to see how that works in practice?</p><Link className="button button-primary" href="/technology">Explore the technology <span aria-hidden="true">→</span></Link></section>
      </main>
      <Footer />
    </>
  );
}