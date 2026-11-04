import Link from "next/link";

export const NAV = [
  { href: "/#services", label: "সেবাসমূহ" },
  { href: "/#how", label: "কীভাবে কাজ করে" },
  { href: "/#visa-types", label: "ভিসার ধরন" },
  { href: "/#documents", label: "প্রয়োজনীয় কাগজ" },
  { href: "/#agency", label: "এজেন্সির জন্য" },
  { href: "/#faq", label: "প্রশ্নোত্তর" },
];

export function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2 font-semibold">
      <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden="true">
        <rect width="32" height="32" rx="8" className="fill-accent" />
        <path d="M9 8h10a4 4 0 0 1 4 4v12H13a4 4 0 0 1-4-4z" fill="none" stroke="white" strokeWidth="2" />
        <circle cx="16" cy="15" r="3.2" fill="none" stroke="white" strokeWidth="1.8" />
        <path d="M12.5 20.5h7" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
      <span>
        Visa <span className="text-saffron">Assistant</span>
      </span>
    </Link>
  );
}

/** Public site header. The mobile menu is a <details> element: works without JavaScript. */
export function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-bg-elevated/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <Logo />
        <nav aria-label="প্রধান মেনু" className="hidden items-center gap-5 text-sm lg:flex">
          {NAV.map((n) => (
            <a key={n.href} href={n.href} className="text-muted transition hover:text-fg">
              {n.label}
            </a>
          ))}
        </nav>
        <div className="hidden items-center gap-2 sm:flex">
          <Link href="/login" className="rounded-lg px-3 py-2 text-sm font-medium hover:text-accent">
            লগইন
          </Link>
          <Link
            href="/register"
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 dark:text-black"
          >
            অ্যাকাউন্ট খুলুন
          </Link>
        </div>
        <details className="group relative lg:hidden">
          <summary
            className="flex cursor-pointer list-none items-center rounded-lg border border-line p-2 [&::-webkit-details-marker]:hidden"
            aria-label="মেনু খুলুন"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
              <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </summary>
          <nav
            aria-label="মোবাইল মেনু"
            className="absolute right-0 mt-2 w-64 rounded-xl border border-line bg-bg-elevated p-2 shadow-lg"
          >
            {NAV.map((n) => (
              <a key={n.href} href={n.href} className="block rounded-lg px-3 py-2 text-sm hover:bg-bg-sunken">
                {n.label}
              </a>
            ))}
            <div className="mt-2 grid grid-cols-2 gap-2 border-t border-line pt-2 sm:hidden">
              <Link href="/login" className="rounded-lg border border-line px-3 py-2 text-center text-sm">
                লগইন
              </Link>
              <Link href="/register" className="rounded-lg bg-accent px-3 py-2 text-center text-sm text-white dark:text-black">
                সাইন আপ
              </Link>
            </div>
          </nav>
        </details>
      </div>
    </header>
  );
}
