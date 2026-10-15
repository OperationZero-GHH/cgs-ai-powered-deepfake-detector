import Link from "next/link";
import type { ReactNode } from "react";
import { FadeScrollArea } from "@/components/fade-scroll-area";

type TocItem = {
  id: string;
  label: string;
};

type LongFormPageProps = {
  eyebrow: string;
  title: string;
  lede: string;
  notice?: ReactNode;
  overviewTitle?: string;
  overviewItems?: string[];
  toc: TocItem[];
  children: ReactNode;
  prevHref?: string;
  prevLabel?: string;
  nextHref?: string;
  nextLabel?: string;
};

export function LongFormPage({
  eyebrow,
  title,
  lede,
  notice,
  overviewTitle,
  overviewItems,
  toc,
  children,
  prevHref,
  prevLabel,
  nextHref,
  nextLabel,
}: LongFormPageProps) {
  return (
    <main id="main-content" className="content-page">
      <div className="container longform-shell">
        <aside className="toc-panel" aria-label="Page sections">
          <p className="toc-label">On this page</p>
          <FadeScrollArea ariaLabel="Page section links" maxHeight="min(55vh, 420px)">
            <nav>
              {toc.map((item) => (
                <a key={item.id} href={`#${item.id}`}>
                  {item.label}
                </a>
              ))}
            </nav>
          </FadeScrollArea>
        </aside>

        <article className="longform-body">
          <header className="page-intro">
            <span className="eyebrow">{eyebrow}</span>
            <h1>{title}</h1>
            <p>{lede}</p>
          </header>

          {notice ? <div>{notice}</div> : null}

          {overviewTitle && overviewItems && overviewItems.length > 0 ? (
            <div className="overview-panel">
              <h3>{overviewTitle}</h3>
              <ul>
                {overviewItems.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {children}

          {(prevHref || nextHref) && (
            <nav className="page-nav" aria-label="Page navigation">
              {prevHref ? (
                <Link href={prevHref}>
                  ← {prevLabel ?? "Previous"}
                </Link>
              ) : <span aria-hidden="true" />}
              {nextHref ? (
                <Link href={nextHref}>
                  {nextLabel ?? "Next"} →
                </Link>
              ) : <span aria-hidden="true" />}
            </nav>
          )}
        </article>
      </div>
    </main>
  );
}
