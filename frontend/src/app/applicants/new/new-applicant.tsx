"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { ApplicantForm } from "@/components/applicant-form";
import { Card } from "@/components/page-shell";
import { Notice } from "@/components/ui";
import { ApiError } from "@/lib/api";
import type { Applicant } from "@/lib/applicants";
import { type BgdData, bgdToApplicant } from "@/lib/bgd";
import { FIELD_LABEL, type PassportData, postFile } from "@/lib/ocr";

type Msg = { tone: "success" | "error" | "info"; text: string } | null;
type Diff = { field: string; form: string; passport: string };

const FILE_INPUT =
  "w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-accent file:px-3 file:py-2 file:text-white dark:file:text-black";

/** Passport values that differ from what is already in the form (from the BGD). */
function compare(form: Partial<Applicant>, p: PassportData): Diff[] {
  const pairs: Array<[keyof Applicant, string | null]> = [
    ["surname", p.surname],
    ["given_name", p.given_name],
    ["passport_number", p.passport_number],
    ["date_of_birth", p.date_of_birth],
    ["passport_expiry_date", p.passport_expiry_date],
    ["gender", p.gender],
  ];
  const norm = (v: unknown) => String(v ?? "").replace(/\s+/g, " ").trim().toUpperCase();
  return pairs
    .filter(([k, v]) => v && norm(form[k]) && norm(form[k]) !== norm(v))
    .map(([k, v]) => ({ field: k, form: norm(form[k]), passport: norm(v) }));
}

export function NewApplicant() {
  const router = useRouter();
  const org = useSearchParams().get("org");
  const valid = !org || /^[0-9a-f-]{36}$/i.test(org);
  const back = org && valid ? `/agency/${org}/applicants` : "/applicants";
  const [prefill, setPrefill] = useState<Partial<Applicant> | null>(null);
  const [formKey, setFormKey] = useState(0);
  const [bgdFile, setBgdFile] = useState<File | null>(null);
  const [bgdMsg, setBgdMsg] = useState<Msg>(null);
  const [ppMsg, setPpMsg] = useState<Msg>(null);
  const [diffs, setDiffs] = useState<Diff[] | null>(null);
  const [busy, setBusy] = useState<"bgd" | "passport" | "save" | null>(null);

  async function readBgd(file: File) {
    setBusy("bgd");
    setBgdMsg(null);
    setDiffs(null);
    try {
      const b = await postFile<BgdData>("/bgd/parse", file);
      setPrefill(bgdToApplicant(b));
      setBgdFile(file);
      setFormKey((k) => k + 1);
      setBgdMsg(
        b.missing.length
          ? { tone: "info", text: `তথ্য বসানো হয়েছে, তবে কিছু ঘর পাওয়া যায়নি: ${b.missing.map((m) => FIELD_LABEL[m] ?? m).join(", ")}। নিচে পূরণ করুন।` }
          : { tone: "success", text: `BGD ${b.application_id ?? ""} থেকে সব তথ্য বসানো হয়েছে। চাইলে পাসপোর্টের ছবি দিয়ে মিলিয়ে নিন, তারপর সংরক্ষণ করুন।` },
      );
    } catch (err) {
      setBgdMsg({ tone: "error", text: err instanceof ApiError ? err.message : "পড়া যায়নি।" });
    } finally {
      setBusy(null);
    }
  }

  async function readPassport(file: File) {
    setBusy("passport");
    setPpMsg(null);
    setDiffs(null);
    try {
      const p = await postFile<PassportData>("/ocr/passport", file);
      if (prefill?.passport_number) {
        // BGD already filled the form: cross-check instead of overwriting
        setDiffs(compare(prefill, p));
        setPpMsg(p.valid ? null : { tone: "info", text: "পাসপোর্টের কিছু অংশ নিশ্চিতভাবে পড়া যায়নি (check digit মেলেনি)।" });
      } else {
        setPrefill({
          surname: p.surname,
          given_name: p.given_name,
          passport_number: p.passport_number,
          date_of_birth: p.date_of_birth ?? "",
          passport_expiry_date: p.passport_expiry_date ?? "",
          gender: p.gender ?? undefined,
          nationality: p.nationality || "BGD",
        });
        setFormKey((k) => k + 1);
        setPpMsg(
          p.valid
            ? { tone: "success", text: "পাসপোর্ট থেকে তথ্য বসানো হয়েছে। সংরক্ষণের আগে প্রতিটি ঘর মিলিয়ে নিন।" }
            : { tone: "info", text: "কিছু তথ্য নিশ্চিতভাবে পড়া যায়নি (check digit মেলেনি)। প্রতিটি ঘর ভালো করে যাচাই করুন।" },
        );
      }
    } catch (err) {
      setPpMsg({ tone: "error", text: err instanceof ApiError ? err.message : "পড়া যায়নি।" });
    } finally {
      setBusy(null);
    }
  }

  async function attachBgd(applicantId: string): Promise<boolean> {
    if (!bgdFile) return true;
    const body = new FormData();
    body.append("kind", "bgd_form");
    body.append("file", bgdFile);
    const r = await fetch(`/api/v1/applicants/${applicantId}/documents`, { method: "POST", body, credentials: "include" });
    return r.ok;
  }

  if (!valid) return <p className="text-sm text-red-600">লিংকটি সঠিক নয়।</p>;
  return (
    <>
      <Link href={back} className="mb-4 inline-block text-sm text-accent">
        ← তালিকায় ফিরুন
      </Link>

      <Card className="border-accent/50">
        <div className="mb-1 flex items-center gap-2">
          <span className="rounded-full bg-accent px-2 py-0.5 text-xs font-semibold text-white dark:text-black">১</span>
          <h2 className="font-semibold">BGD ফর্মের PDF দিন</h2>
        </div>
        <p className="mb-4 text-sm text-muted">
          অনলাইন আবেদন শেষে যে PDF (BGD…) ডাউনলোড হয়, সেটি দিন। নাম, পাসপোর্ট, ঠিকানা, পরিবার, ভিসা ও যাত্রার তথ্য নিজে থেকে
          বসে যাবে, আর সংরক্ষণের সময় PDF-টি ডকুমেন্টে জমা হবে।
        </p>
        {bgdMsg && <Notice tone={bgdMsg.tone}>{bgdMsg.text}</Notice>}
        <input
          type="file"
          accept="application/pdf"
          disabled={busy !== null}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void readBgd(f);
            e.target.value = "";
          }}
          className={FILE_INPUT}
        />
        {busy === "bgd" && <p className="mt-3 text-sm text-muted">পড়া হচ্ছে…</p>}
        {bgdFile && busy !== "bgd" && <p className="mt-2 text-xs text-muted">📎 {bgdFile.name}</p>}
      </Card>

      <Card className="border-dashed">
        <div className="mb-1 flex items-center gap-2">
          <span className="rounded-full bg-bg-sunken px-2 py-0.5 text-xs font-semibold">২</span>
          <h2 className="font-semibold">পাসপোর্টের ছবি দিয়ে মিলিয়ে নিন (ঐচ্ছিক)</h2>
        </div>
        <p className="mb-4 text-sm text-muted">
          {prefill?.passport_number
            ? "পাসপোর্টের তথ্য পাতার ছবি দিলে BGD-র নাম, নম্বর, জন্মতারিখ ও মেয়াদ পাসপোর্টের সাথে মেলানো হবে। ছবিটি সংরক্ষণ করা হয় না।"
            : "BGD না থাকলে পাসপোর্টের ছবি থেকেও নাম, নম্বর, জন্মতারিখ ও মেয়াদ বসানো যায়। ছবিটি সংরক্ষণ করা হয় না।"}
        </p>
        {ppMsg && <Notice tone={ppMsg.tone}>{ppMsg.text}</Notice>}
        {diffs && diffs.length === 0 && <Notice tone="success">✓ BGD ও পাসপোর্টের তথ্য মিলেছে।</Notice>}
        {diffs && diffs.length > 0 && (
          <div className="mb-4 rounded-lg border border-amber-400 p-3 text-sm">
            <p className="mb-2 font-medium text-amber-600">⚠ BGD ও পাসপোর্টে {diffs.length}টি অমিল। IVAC-এ জমার আগে BGD ঠিক করুন:</p>
            <table className="w-full text-xs">
              <thead className="text-muted">
                <tr>
                  <th className="pr-2 text-left font-normal">ঘর</th>
                  <th className="pr-2 text-left font-normal">BGD-তে</th>
                  <th className="text-left font-normal">পাসপোর্টে</th>
                </tr>
              </thead>
              <tbody>
                {diffs.map((d) => (
                  <tr key={d.field}>
                    <td className="pr-2">{FIELD_LABEL[d.field] ?? d.field}</td>
                    <td className="pr-2 font-mono">{d.form}</td>
                    <td className="font-mono">{d.passport}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <input
          type="file"
          accept="image/jpeg,image/png"
          disabled={busy !== null}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void readPassport(f);
            e.target.value = "";
          }}
          className={FILE_INPUT}
        />
        {busy === "passport" && <p className="mt-3 text-sm text-muted">পড়া হচ্ছে… (কয়েক সেকেন্ড লাগতে পারে)</p>}
      </Card>

      <ApplicantForm
        key={formKey}
        initial={prefill as Applicant | undefined}
        createPath={org ? `/orgs/${org}/applicants` : "/applicants"}
        onSaved={async (s) => {
          setBusy("save");
          const attached = await attachBgd(s.applicant.id);
          const warnings = [...s.warnings];
          if (!attached) warnings.push("আবেদনকারী সংরক্ষিত হয়েছে, কিন্তু BGD PDF ডকুমেন্টে জমা হয়নি। ডকুমেন্ট অংশ থেকে আবার আপলোড করুন।");
          const w = warnings.length ? `?w=${encodeURIComponent(warnings.join("\n"))}` : "";
          router.push(`/applicants/${s.applicant.id}${w}`);
        }}
      />
    </>
  );
}
