import Link from "next/link";
import type { ReactNode } from "react";

/** Signed-in page layout: small top bar + content column. */
export function PageShell({ title, children, actions }: { title: string; children: ReactNode; actions?: ReactNode }) {
  return (
    <>
      <header className="border-b border-line bg-bg-elevated">
        <nav className="mx-auto flex max-w-4xl items-center gap-4 px-4 py-3 text-sm">
          <Link href="/" className="font-semibold text-accent">
            Visa Assistant
          </Link>
          <Link href="/account" className="text-muted hover:text-fg">
            অ্যাকাউন্ট
          </Link>
          <Link href="/applicants" className="text-muted hover:text-fg">
            আবেদনকারী
          </Link>
          <Link href="/agency" className="text-muted hover:text-fg">
            এজেন্সি
          </Link>
        </nav>
      </header>
      <main className="mx-auto w-full max-w-4xl px-4 py-8 sm:py-12">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold">{title}</h1>
          {actions}
        </div>
        {children}
      </main>
    </>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`mb-6 rounded-2xl border border-line bg-bg-elevated p-6 ${className}`}>{children}</section>;
}
