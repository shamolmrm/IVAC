import Link from "next/link";
import { Logo, NAV } from "./site-header";

export function SiteFooter() {
  return (
    <footer className="border-t border-line bg-bg-elevated">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 sm:grid-cols-3">
        <div>
          <Logo />
          <p className="mt-3 text-sm text-muted">
            ভারতীয় ভিসা আবেদনকারী ও এজেন্সির জন্য ডকুমেন্ট ব্যবস্থাপনা ও আবেদন প্রস্তুতির সফটওয়্যার।
          </p>
        </div>
        <nav aria-label="ফুটার মেনু" className="grid grid-cols-2 gap-2 text-sm">
          {NAV.map((n) => (
            <a key={n.href} href={n.href} className="text-muted hover:text-fg">
              {n.label}
            </a>
          ))}
        </nav>
        <div className="text-sm">
          <Link href="/register" className="block text-accent">
            অ্যাকাউন্ট খুলুন →
          </Link>
          <Link href="/login" className="mt-2 block text-muted hover:text-fg">
            লগইন
          </Link>
        </div>
      </div>
      <div className="border-t border-line">
        <p className="mx-auto max-w-6xl px-4 py-4 text-xs text-muted">
          এটি IVAC, ভারতীয় হাইকমিশন বা কোনো সরকারি প্রতিষ্ঠানের অফিসিয়াল ওয়েবসাইট নয় এবং তাদের সঙ্গে যুক্ত নয়। ভিসা প্রদানের
          সিদ্ধান্ত সম্পূর্ণ সংশ্লিষ্ট কর্তৃপক্ষের। · Design &amp; development: Super Soft Ltd.
        </p>
      </div>
    </footer>
  );
}
