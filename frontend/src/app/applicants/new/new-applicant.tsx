"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { ApplicantForm } from "@/components/applicant-form";
import { Card } from "@/components/page-shell";
import { Notice } from "@/components/ui";
import { ApiError } from "@/lib/api";
import type { Applicant } from "@/lib/applicants";
import { type PassportData, postFile } from "@/lib/ocr";

export function NewApplicant() {
  const router = useRouter();
  const org = useSearchParams().get("org");
  const valid = !org || /^[0-9a-f-]{36}$/i.test(org);
  const back = org && valid ? `/agency/${org}/applicants` : "/applicants";
  const [prefill, setPrefill] = useState<Partial<Applicant> | null>(null);
  const [formKey, setFormKey] = useState(0);
  const [msg, setMsg] = useState<{ tone: "success" | "error" | "info"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  async function readPassport(file: File) {
    setBusy(true);
    setMsg(null);
    try {
      const p = await postFile<PassportData>("/ocr/passport", file);
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
      setMsg(
        p.valid
          ? { tone: "success", text: "পাসপোর্ট থেকে তথ্য বসানো হয়েছে। সংরক্ষণের আগে প্রতিটি ঘর মিলিয়ে নিন।" }
          : { tone: "info", text: "কিছু তথ্য নিশ্চিতভাবে পড়া যায়নি (check digit মেলেনি)। প্রতিটি ঘর ভালো করে যাচাই করুন।" },
      );
    } catch (err) {
      setMsg({ tone: "error", text: err instanceof ApiError ? err.message : "পড়া যায়নি।" });
    } finally {
      setBusy(false);
    }
  }

  if (!valid) return <p className="text-sm text-red-600">লিংকটি সঠিক নয়।</p>;
  return (
    <>
      <Link href={back} className="mb-4 inline-block text-sm text-accent">
        ← তালিকায় ফিরুন
      </Link>
      <Card className="border-dashed">
        <h2 className="mb-1 font-semibold">পাসপোর্টের ছবি থেকে স্বয়ংক্রিয় পূরণ</h2>
        <p className="mb-4 text-sm text-muted">
          পাসপোর্টের তথ্য পাতার পরিষ্কার ছবি (JPG/PNG) দিন। নিচের দুই লাইনের লেখা (MRZ) পড়ে নাম, নম্বর, জন্মতারিখ ও মেয়াদ বসানো
          হবে। ছবিটি সংরক্ষণ করা হয় না।
        </p>
        {msg && <Notice tone={msg.tone}>{msg.text}</Notice>}
        <input
          type="file"
          accept="image/jpeg,image/png"
          disabled={busy}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void readPassport(f);
            e.target.value = "";
          }}
          className="w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-accent file:px-3 file:py-2 file:text-white dark:file:text-black"
        />
        {busy && <p className="mt-3 text-sm text-muted">পড়া হচ্ছে… (কয়েক সেকেন্ড লাগতে পারে)</p>}
      </Card>
      <ApplicantForm
        key={formKey}
        initial={prefill as Applicant | undefined}
        createPath={org ? `/orgs/${org}/applicants` : "/applicants"}
        onSaved={(s) => {
          const w = s.warnings.length ? `?w=${encodeURIComponent(s.warnings.join("\n"))}` : "";
          router.push(`/applicants/${s.applicant.id}${w}`);
        }}
      />
    </>
  );
}
