import Link from "next/link";
import type { ReactNode } from "react";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

type Service = { title: string; text: string; icon: ReactNode; live: boolean };

const icon = (d: string) => (
  <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
    <path d={d} strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const SERVICES: Service[] = [
  {
    title: "নিরাপদ অ্যাকাউন্ট",
    text: "ইমেইল ও মোবাইল যাচাইসহ ব্যক্তিগত অ্যাকাউন্ট। প্রতিটি লগইন ও পরিবর্তনের নিরাপত্তা লগ।",
    icon: icon("M12 3l7 3v5c0 4.5-3 8.5-7 10-4-1.5-7-5.5-7-10V6z M9 12l2 2 4-4"),
    live: true,
  },
  {
    title: "ডকুমেন্ট আপলোড",
    text: "পাসপোর্ট, ছবি, BGD ফর্ম, ব্যাংক স্টেটমেন্ট এক জায়গায়, এনক্রিপ্ট করে সংরক্ষিত।",
    icon: icon("M12 16V4m0 0l-4 4m4-4l4 4M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"),
    live: true,
  },
  {
    title: "স্বয়ংক্রিয় তথ্য পাঠ (OCR)",
    text: "পাসপোর্টের MRZ থেকে নাম, জন্মতারিখ, পাসপোর্ট নম্বর ও মেয়াদ নিজে থেকেই পড়ে নেওয়া।",
    icon: icon("M4 7V5a1 1 0 0 1 1-1h2M17 4h2a1 1 0 0 1 1 1v2M20 17v2a1 1 0 0 1-1 1h-2M7 20H5a1 1 0 0 1-1-1v-2M8 10h8M8 14h5"),
    live: true,
  },
  {
    title: "তথ্য যাচাই",
    text: "পাসপোর্ট ও BGD ফর্মের তথ্য মিলিয়ে ভুল বা অমিল আগেই ধরিয়ে দেওয়া।",
    icon: icon("M9 12l2 2 4-4M7 3h10a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"),
    live: false,
  },
  {
    title: "আবেদনের অবস্থা ট্র্যাকিং",
    text: "প্রতিটি আবেদনের আলাদা টাইমলাইন: কাগজ জমা থেকে appointment পর্যন্ত।",
    icon: icon("M4 6h16M4 12h10M4 18h6M18 15l2 2-2 2"),
    live: false,
  },
  {
    title: "পেমেন্ট ও ইনভয়েস",
    text: "সার্ভিস চার্জের আলাদা হিসাব, রসিদ ও PDF ইনভয়েস।",
    icon: icon("M3 7h18v10H3zM3 10h18M7 15h3"),
    live: false,
  },
];

const STEPS = [
  { title: "অ্যাকাউন্ট খুলুন", text: "ইমেইল ও মোবাইল নম্বর দিয়ে কয়েক মিনিটে নিবন্ধন।" },
  { title: "কাগজ আপলোড করুন", text: "পাসপোর্ট, ছবি ও প্রয়োজনীয় ডকুমেন্টের ছবি বা PDF দিন।" },
  { title: "তথ্য যাচাই", text: "সিস্টেম তথ্য পড়ে মিলিয়ে দেখবে; ভুল থাকলে জানিয়ে দেবে।" },
  { title: "আবেদন প্রস্তুত", text: "যাচাই করা তথ্য ও চেকলিস্ট দিয়ে IVAC-এ আবেদন সহজ ও নির্ভুল।" },
];

const VISA_TYPES = [
  { name: "ট্যুরিস্ট", text: "ভ্রমণ, আত্মীয়-স্বজনের সঙ্গে দেখা" },
  { name: "মেডিকেল", text: "ভারতে চিকিৎসার জন্য" },
  { name: "মেডিকেল অ্যাটেনডেন্ট", text: "রোগীর সঙ্গী হিসেবে" },
  { name: "বিজনেস", text: "ব্যবসায়িক সফর ও মিটিং" },
  { name: "স্টুডেন্ট", text: "ভারতে পড়াশোনা" },
  { name: "এন্ট্রি ও অন্যান্য", text: "অন্যান্য প্রযোজ্য ক্যাটাগরি" },
];

const DOCUMENTS = [
  "বৈধ পাসপোর্ট (মেয়াদ পর্যাপ্ত থাকতে হবে)",
  "সাম্প্রতিক রঙিন ছবি (সাদা ব্যাকগ্রাউন্ড)",
  "অনলাইন আবেদন ফর্মের প্রিন্ট (BGD নম্বরসহ)",
  "জাতীয় পরিচয়পত্র বা ঠিকানার প্রমাণ",
  "ব্যাংক স্টেটমেন্ট বা আর্থিক সক্ষমতার প্রমাণ",
  "আগের ভারতীয় ভিসার কপি (থাকলে)",
];

const FAQ = [
  {
    q: "এটি কি IVAC-এর অফিসিয়াল ওয়েবসাইট?",
    a: "না। এটি একটি স্বাধীন সফটওয়্যার, যা আবেদনকারী ও এজেন্সিকে কাগজপত্র গুছিয়ে নির্ভুল আবেদন প্রস্তুত করতে সাহায্য করে। IVAC বা ভারতীয় হাইকমিশনের সঙ্গে এর কোনো সম্পর্ক নেই।",
  },
  {
    q: "আপনারা কি appointment নিশ্চিত করে দেন?",
    a: "না। Appointment ও ভিসা প্রদান সম্পূর্ণ IVAC ও সংশ্লিষ্ট কর্তৃপক্ষের সিদ্ধান্ত। আমরা তথ্য ও কাগজ প্রস্তুত রাখতে সাহায্য করি, যাতে আবেদনে ভুল না হয়।",
  },
  {
    q: "আমার পাসপোর্টের তথ্য কি নিরাপদ?",
    a: "ডকুমেন্ট এনক্রিপ্ট করে সংরক্ষণ করা হয়, শুধু অনুমোদিত ব্যক্তি দেখতে পারেন, এবং প্রতিটি অ্যাক্সেসের লগ রাখা হয়। এক এজেন্সির তথ্য অন্য এজেন্সি কখনো দেখতে পায় না।",
  },
  {
    q: "সরকারি ভিসা ফি কোথায় দিতে হবে?",
    a: "সরকারি ফি IVAC-এর অনুমোদিত পদ্ধতিতেই দিতে হবে। এই সাইটে শুধু আমাদের সার্ভিস চার্জের হিসাব থাকবে।",
  },
  {
    q: "কাগজপত্রের তালিকা কি সবসময় একই?",
    a: "না। ভিসার ধরন অনুযায়ী তালিকা বদলায় এবং কর্তৃপক্ষ সময়ে সময়ে নিয়ম পরিবর্তন করে। আবেদনের আগে IVAC-এর সর্বশেষ নির্দেশনা অবশ্যই দেখে নিন।",
  },
];

function Badge({ live }: { live: boolean }) {
  return live ? (
    <span className="rounded-full bg-accent-soft px-2 py-0.5 text-xs font-medium text-accent">চালু</span>
  ) : (
    <span className="rounded-full bg-saffron-soft px-2 py-0.5 text-xs font-medium text-saffron">শীঘ্রই</span>
  );
}

function SectionTitle({ eyebrow, title, text }: { eyebrow: string; title: string; text?: string }) {
  return (
    <div className="mx-auto mb-10 max-w-2xl text-center">
      <p className="mb-2 text-sm font-semibold text-saffron">{eyebrow}</p>
      <h2 className="text-2xl font-bold sm:text-3xl">{title}</h2>
      {text && <p className="mt-3 text-muted">{text}</p>}
    </div>
  );
}

function HeroArt() {
  // Abstract passport + checklist illustration (no official symbols).
  return (
    <svg viewBox="0 0 320 260" className="w-full max-w-sm drop-shadow-2xl" aria-hidden="true">
      <rect x="40" y="20" width="170" height="220" rx="16" fill="#0b3b3a" stroke="rgba(255,255,255,.25)" />
      <rect x="56" y="38" width="138" height="184" rx="10" fill="none" stroke="rgba(245,165,74,.6)" strokeDasharray="4 4" />
      <circle cx="125" cy="105" r="32" fill="none" stroke="#f5a54a" strokeWidth="3" />
      <path d="M93 105h64M125 73c-12 14-12 50 0 64M125 73c12 14 12 50 0 64" stroke="#f5a54a" strokeWidth="2" fill="none" />
      <text x="125" y="170" textAnchor="middle" fill="#f5a54a" fontSize="14" fontWeight="700" letterSpacing="3">
        PASSPORT
      </text>
      <rect x="85" y="188" width="80" height="6" rx="3" fill="rgba(255,255,255,.25)" />
      <rect x="170" y="90" width="130" height="150" rx="14" fill="white" />
      {[0, 1, 2, 3].map((i) => (
        <g key={i} transform={`translate(186 ${112 + i * 30})`}>
          <rect width="16" height="16" rx="4" fill={i < 3 ? "#0f766e" : "#e3e6ec"} />
          {i < 3 && <path d="M4 8l3 3 5-6" stroke="white" strokeWidth="2" fill="none" strokeLinecap="round" />}
          <rect x="26" y="4" width={i === 3 ? 60 : 78} height="8" rx="4" fill="#e3e6ec" />
        </g>
      ))}
    </svg>
  );
}

export default function HomePage() {
  return (
    <>
      <SiteHeader />
      <main>
        {/* Hero */}
        <section className="hero-bg text-white">
          <div className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-16 sm:py-24 lg:grid-cols-[1.2fr_1fr]">
            <div>
              <p className="mb-4 inline-block rounded-full border border-white/30 px-3 py-1 text-sm text-white/90">
                ভারতীয় ভিসা আবেদন সহায়তা · বাংলাদেশ
              </p>
              <h1 className="text-3xl font-bold leading-tight sm:text-5xl">
                ভারতীয় ভিসার আবেদন হোক <span className="text-[#f5a54a]">সহজ, গোছানো ও নির্ভুল</span>
              </h1>
              <p className="mt-5 max-w-xl text-lg text-white/80">
                কাগজপত্র এক জায়গায় রাখুন, তথ্য স্বয়ংক্রিয়ভাবে যাচাই করুন, আর প্রতিটি আবেদনের অবস্থা দেখুন। আবেদনকারী ও
                ট্রাভেল এজেন্সি দুজনের জন্যই।
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link
                  href="/register"
                  className="rounded-xl bg-[#f5a54a] px-6 py-3 font-semibold text-[#1d2433] transition hover:brightness-105"
                >
                  অ্যাকাউন্ট খুলুন
                </Link>
                <Link href="/login" className="rounded-xl border border-white/40 px-6 py-3 font-semibold hover:bg-white/10">
                  লগইন
                </Link>
              </div>
              <p className="mt-6 text-xs text-white/60">IVAC বা কোনো সরকারি প্রতিষ্ঠানের অফিসিয়াল সেবা নয়।</p>
            </div>
            <div className="flex justify-center">
              <HeroArt />
            </div>
          </div>
        </section>

        {/* Services */}
        <section id="services" className="scroll-mt-20 px-4 py-16 sm:py-20">
          <div className="mx-auto max-w-6xl">
            <SectionTitle
              eyebrow="সেবাসমূহ"
              title="আমরা কী কী কাজ করি"
              text="আবেদনের প্রস্তুতির প্রতিটি ধাপ এক প্ল্যাটফর্মে। নতুন সেবাগুলো ধাপে ধাপে চালু হচ্ছে।"
            />
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {SERVICES.map((s) => (
                <article key={s.title} className="rounded-2xl border border-line bg-bg-elevated p-6 transition hover:-translate-y-0.5 hover:shadow-lg">
                  <div className="mb-4 flex items-center justify-between">
                    <span className="grid h-11 w-11 place-items-center rounded-xl bg-accent-soft text-accent">{s.icon}</span>
                    <Badge live={s.live} />
                  </div>
                  <h3 className="mb-2 font-semibold">{s.title}</h3>
                  <p className="text-sm text-muted">{s.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* How it works */}
        <section id="how" className="scroll-mt-20 bg-bg-sunken px-4 py-16 sm:py-20">
          <div className="mx-auto max-w-6xl">
            <SectionTitle eyebrow="কীভাবে কাজ করে" title="চার ধাপে আবেদন প্রস্তুত" />
            <ol className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {STEPS.map((s, i) => (
                <li key={s.title} className="relative rounded-2xl border border-line bg-bg-elevated p-6">
                  <span className="mb-4 grid h-10 w-10 place-items-center rounded-full bg-saffron-soft font-bold text-saffron">
                    {(i + 1).toLocaleString("bn-BD")}
                  </span>
                  <h3 className="mb-2 font-semibold">{s.title}</h3>
                  <p className="text-sm text-muted">{s.text}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* Visa types */}
        <section id="visa-types" className="scroll-mt-20 px-4 py-16 sm:py-20">
          <div className="mx-auto max-w-6xl">
            <SectionTitle
              eyebrow="ভিসার ধরন"
              title="যেসব ভারতীয় ভিসার প্রস্তুতিতে সাহায্য করি"
              text="প্রতিটি ধরনের জন্য আলাদা কাগজের চেকলিস্ট থাকবে।"
            />
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {VISA_TYPES.map((v) => (
                <div key={v.name} className="flex items-center gap-4 rounded-2xl border border-line bg-bg-elevated p-5">
                  <span className="h-10 w-1.5 shrink-0 rounded-full bg-gradient-to-b from-saffron to-accent" />
                  <div>
                    <h3 className="font-semibold">{v.name} ভিসা</h3>
                    <p className="text-sm text-muted">{v.text}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Documents */}
        <section id="documents" className="scroll-mt-20 bg-bg-sunken px-4 py-16 sm:py-20">
          <div className="mx-auto grid max-w-6xl items-center gap-10 lg:grid-cols-2">
            <div>
              <p className="mb-2 text-sm font-semibold text-saffron">প্রয়োজনীয় কাগজ</p>
              <h2 className="text-2xl font-bold sm:text-3xl">সাধারণত যেসব কাগজ লাগে</h2>
              <p className="mt-3 text-muted">
                ভিসার ধরন অনুযায়ী তালিকা বদলায়। আবেদনের আগে IVAC-এর সর্বশেষ নির্দেশনা অবশ্যই মিলিয়ে নিন।
              </p>
            </div>
            <ul className="grid gap-3">
              {DOCUMENTS.map((d) => (
                <li key={d} className="flex items-start gap-3 rounded-xl border border-line bg-bg-elevated p-4 text-sm">
                  <svg viewBox="0 0 24 24" className="mt-0.5 h-5 w-5 shrink-0 text-accent" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <path d="M5 12l4 4 10-10" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  {d}
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* Agencies */}
        <section id="agency" className="scroll-mt-20 px-4 py-16 sm:py-20">
          <div className="mx-auto max-w-6xl overflow-hidden rounded-3xl border border-line bg-bg-elevated">
            <div className="grid gap-8 p-8 sm:p-12 lg:grid-cols-[1.3fr_1fr] lg:items-center">
              <div>
                <p className="mb-2 text-sm font-semibold text-saffron">ট্রাভেল এজেন্সির জন্য</p>
                <h2 className="text-2xl font-bold sm:text-3xl">শত শত আবেদনকারী, একটি ড্যাশবোর্ড</h2>
                <ul className="mt-5 grid gap-2 text-sm text-muted">
                  <li>✓ Owner, Manager ও Agent: আলাদা অনুমতি <Badge live /></li>
                  <li>✓ Staff আমন্ত্রণ ও ব্যবস্থাপনা <Badge live /></li>
                  <li>✓ এক এজেন্সির তথ্য অন্য এজেন্সি দেখতে পায় না <Badge live /></li>
                  <li>✓ Applicant ভাগ করে দেওয়া, Excel/CSV থেকে একসঙ্গে import <Badge live={false} /></li>
                  <li>✓ দৈনিক ও মাসিক রিপোর্ট, আয়-ব্যয়ের হিসাব <Badge live={false} /></li>
                </ul>
              </div>
              <div className="rounded-2xl bg-accent-soft p-6 text-center">
                <p className="mb-4 font-semibold">আপনার এজেন্সি যুক্ত করুন</p>
                <Link
                  href="/register?next=/agency"
                  className="inline-block rounded-xl bg-accent px-6 py-3 font-semibold text-white dark:text-black"
                >
                  এজেন্সি অ্যাকাউন্ট খুলুন
                </Link>
                <p className="mt-3 text-xs text-muted">অনুমোদনের পর staff যোগ করতে পারবেন।</p>
              </div>
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section id="faq" className="scroll-mt-20 bg-bg-sunken px-4 py-16 sm:py-20">
          <div className="mx-auto max-w-3xl">
            <SectionTitle eyebrow="প্রশ্নোত্তর" title="সাধারণ প্রশ্ন" />
            <div className="grid gap-3">
              {FAQ.map((f) => (
                <details key={f.q} className="group rounded-xl border border-line bg-bg-elevated p-5">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-medium [&::-webkit-details-marker]:hidden">
                    {f.q}
                    <span className="text-accent transition group-open:rotate-45">+</span>
                  </summary>
                  <p className="mt-3 text-sm text-muted">{f.a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="px-4 py-16">
          <div className="hero-bg mx-auto max-w-6xl rounded-3xl px-6 py-12 text-center text-white">
            <h2 className="text-2xl font-bold sm:text-3xl">আজই আবেদনের প্রস্তুতি শুরু করুন</h2>
            <p className="mx-auto mt-3 max-w-xl text-white/80">কয়েক মিনিটেই অ্যাকাউন্ট খুলে কাগজপত্র গোছানো শুরু করুন।</p>
            <div className="mt-6 flex flex-wrap justify-center gap-3">
              <Link href="/register" className="rounded-xl bg-[#f5a54a] px-6 py-3 font-semibold text-[#1d2433]">
                সাইন আপ
              </Link>
              <Link href="/login" className="rounded-xl border border-white/40 px-6 py-3 font-semibold hover:bg-white/10">
                লগইন
              </Link>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
