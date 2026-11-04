"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ApplicantForm } from "@/components/applicant-form";
import { DocumentsPanel } from "@/components/documents-panel";
import { Card, PageShell } from "@/components/page-shell";
import { Notice } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { type Applicant, daysLeft, GENDER_LABEL, MARITAL_LABEL, VISA_LABEL } from "@/lib/applicants";
import { formatDate } from "@/lib/orgs";

const DIRECT_ORG = "00000000-0000-0000-0000-000000000001";

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <>
      <dt className="text-muted">{label}</dt>
      <dd className="break-words">{value || "—"}</dd>
    </>
  );
}

export function ApplicantDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const initialWarnings = useSearchParams().get("w");
  const [a, setA] = useState<Applicant | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [warnings, setWarnings] = useState<string[]>(initialWarnings ? initialWarnings.split("\n") : []);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api<Applicant>(`/applicants/${id}`)
      .then(setA)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) router.replace(`/login?next=/applicants/${id}`);
        else setError(err instanceof ApiError ? err.message : "লোড করা যায়নি।");
      });
  }, [id, router]);

  if (error)
    return (
      <PageShell title="আবেদনকারী">
        <Notice tone="error">{error}</Notice>
      </PageShell>
    );
  if (!a) return <Notice>লোড হচ্ছে…</Notice>;

  const back = a.organization_id === DIRECT_ORG ? "/applicants" : `/agency/${a.organization_id}/applicants`;
  const left = daysLeft(a.passport_expiry_date);

  async function archive() {
    if (!a || !window.confirm(`${a.given_name} ${a.surname}-কে তালিকা থেকে সরাবেন?`)) return;
    try {
      await api(`/applicants/${a.id}`, { method: "DELETE" });
      router.push(back);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "সরানো যায়নি।");
    }
  }

  return (
    <PageShell
      title={`${a.given_name} ${a.surname}`}
      actions={
        !editing && (
          <div className="flex gap-2">
            <button
              onClick={() => {
                setEditing(true);
                setSaved(false);
              }}
              className="rounded-lg border border-line px-3 py-1.5 text-sm hover:border-accent"
            >
              সম্পাদনা
            </button>
            <button onClick={archive} className="rounded-lg border border-red-300 px-3 py-1.5 text-sm text-red-600">
              সরান
            </button>
          </div>
        )
      }
    >
      <Link href={back} className="mb-4 inline-block text-sm text-accent">
        ← তালিকায় ফিরুন
      </Link>
      {saved && <Notice tone="success">পরিবর্তন সংরক্ষণ হয়েছে।</Notice>}
      {warnings.map((w) => (
        <Notice key={w}>⚠ {w}</Notice>
      ))}

      {editing ? (
        <ApplicantForm
          key={a.updated_at ?? a.id}
          initial={a}
          onSaved={(s) => {
            setA(s.applicant);
            setWarnings(s.warnings);
            setEditing(false);
            setSaved(true);
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
        />
      ) : (
        <>
          <Card>
            <h2 className="mb-4 font-semibold">পাসপোর্ট</h2>
            <dl className="grid gap-3 text-sm sm:grid-cols-[11rem_1fr]">
              <Row label="পাসপোর্ট নম্বর" value={<span className="font-mono">{a.passport_number}</span>} />
              <Row label="ইস্যুর তারিখ" value={formatDate(a.passport_issue_date)} />
              <Row
                label="মেয়াদ শেষ"
                value={
                  <span className={left < 183 ? "text-amber-600" : ""}>
                    {formatDate(a.passport_expiry_date)}
                    {left < 183 && " (৬ মাসের কম বাকি)"}
                  </span>
                }
              />
              <Row label="ইস্যুর স্থান" value={a.passport_issue_place} />
              <Row label="NID" value={a.nid_number && <span className="font-mono">{a.nid_number}</span>} />
              <Row label="ভিসার ধরন" value={VISA_LABEL[a.visa_type]} />
            </dl>
          </Card>
          <DocumentsPanel
            applicantId={a.id}
            onProfileChanged={() => {
              api<Applicant>(`/applicants/${a.id}`).then((fresh) => {
                setA(fresh);
                setSaved(true);
                window.scrollTo({ top: 0, behavior: "smooth" });
              });
            }}
          />
          <Card>
            <h2 className="mb-4 font-semibold">ব্যক্তিগত তথ্য</h2>
            <dl className="grid gap-3 text-sm sm:grid-cols-[11rem_1fr]">
              <Row label="লিঙ্গ" value={GENDER_LABEL[a.gender]} />
              <Row label="জন্মতারিখ" value={formatDate(a.date_of_birth)} />
              <Row label="জন্মস্থান" value={a.place_of_birth} />
              <Row label="বৈবাহিক অবস্থা" value={a.marital_status && MARITAL_LABEL[a.marital_status]} />
              <Row label="পিতা" value={a.father_name} />
              <Row label="মাতা" value={a.mother_name} />
              <Row label="স্বামী/স্ত্রী" value={a.spouse_name} />
              <Row label="পেশা" value={a.occupation} />
            </dl>
          </Card>
          <Card>
            <h2 className="mb-4 font-semibold">যোগাযোগ</h2>
            <dl className="grid gap-3 text-sm sm:grid-cols-[11rem_1fr]">
              <Row label="মোবাইল" value={a.phone} />
              <Row label="ইমেইল" value={a.email} />
              <Row label="বর্তমান ঠিকানা" value={a.present_address} />
              <Row label="স্থায়ী ঠিকানা" value={a.permanent_address} />
              <Row label="নোট" value={a.notes && <span className="whitespace-pre-line">{a.notes}</span>} />
            </dl>
          </Card>
          <p className="text-xs text-muted">
            যোগ করা হয়েছে {formatDate(a.created_at)} · সর্বশেষ পরিবর্তন {formatDate(a.updated_at)} · এই পেজ দেখার তথ্য নিরাপত্তা লগে
            রাখা হয়।
          </p>
        </>
      )}
    </PageShell>
  );
}
