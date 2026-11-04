import Link from "next/link";

export default function HomePage() {
  return (
    <main className="grid min-h-screen place-items-center px-4 py-10">
      <div className="w-full max-w-xl rounded-2xl border border-line bg-bg-elevated p-8">
        <span className="mb-4 inline-block rounded-full border border-accent px-3 py-0.5 text-sm text-accent">
          উন্নয়নাধীন
        </span>
        <h1 className="mb-2 text-2xl font-semibold">Visa Application Assistant</h1>
        <p className="mb-6 text-muted">
          ভারতীয় ভিসা আবেদনকারীদের জন্য ডকুমেন্ট ব্যবস্থাপনা, তথ্য যাচাই ও আবেদন প্রস্তুতির সফটওয়্যার।
        </p>
        <div className="flex flex-wrap gap-3">
          <Link href="/register" className="rounded-lg bg-accent px-4 py-2 font-medium text-white dark:text-black">
            অ্যাকাউন্ট খুলুন
          </Link>
          <Link href="/login" className="rounded-lg border border-line px-4 py-2 font-medium hover:border-accent">
            লগইন
          </Link>
        </div>
        <p className="mt-6 border-t border-line pt-3 text-xs text-muted">
          এটি IVAC বা কোনো সরকারি প্রতিষ্ঠানের অফিসিয়াল ওয়েবসাইট নয় এবং তাদের সঙ্গে যুক্ত নয়। Design
          &amp; development: Super Soft Ltd.
        </p>
      </div>
    </main>
  );
}
