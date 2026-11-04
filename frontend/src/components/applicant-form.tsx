"use client";

import { useState } from "react";
import { Button, Field, Notice } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import {
  type Applicant,
  GENDER_LABEL,
  MARITAL_LABEL,
  type Saved,
  VISA_LABEL,
} from "@/lib/applicants";

type Props = {
  /** POST endpoint for a new applicant, or undefined when editing */
  createPath?: string;
  initial?: Applicant;
  onSaved: (saved: Saved) => void;
};

const TEXT = [
  "surname",
  "given_name",
  "place_of_birth",
  "father_name",
  "mother_name",
  "spouse_name",
  "passport_number",
  "passport_issue_place",
  "nid_number",
  "phone",
  "email",
  "present_address",
  "permanent_address",
  "occupation",
  "notes",
] as const;

function Select({
  label,
  name,
  options,
  defaultValue,
  required,
}: {
  label: string;
  name: string;
  options: Record<string, string>;
  defaultValue?: string | null;
  required?: boolean;
}) {
  return (
    <label className="mb-4 block">
      <span className="mb-1 block text-sm font-medium">{label}</span>
      <select
        name={name}
        defaultValue={defaultValue ?? ""}
        required={required}
        className="w-full rounded-lg border border-line bg-bg px-3 py-2 outline-none focus:border-accent"
      >
        <option value="">— নির্বাচন করুন —</option>
        {Object.entries(options).map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </label>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <fieldset className="mb-6 rounded-xl border border-line p-4 sm:p-5">
      <legend className="px-2 text-sm font-semibold text-accent">{title}</legend>
      <div className="grid gap-x-4 sm:grid-cols-2">{children}</div>
    </fieldset>
  );
}

export function ApplicantForm({ createPath, initial, onSaved }: Props) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const v = (k: keyof Applicant) => (initial?.[k] as string | null | undefined) ?? "";

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const body: Record<string, string | null> = {};
    for (const k of TEXT) body[k] = String(form.get(k) ?? "").trim() || null;
    for (const k of ["gender", "marital_status", "visa_type", "date_of_birth", "passport_issue_date", "passport_expiry_date"]) {
      body[k] = String(form.get(k) ?? "") || null;
    }
    body.nationality = initial?.nationality || "BGD";
    setBusy(true);
    setError(null);
    try {
      const saved = await api<Saved>(createPath ?? `/applicants/${initial?.id}`, {
        method: createPath ? "POST" : "PATCH",
        body: JSON.stringify(body),
      });
      onSaved(saved);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "সংরক্ষণ করা যায়নি।");
      setBusy(false);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  return (
    <form onSubmit={onSubmit}>
      {error && <Notice tone="error">{error}</Notice>}
      <Group title="পরিচয় (পাসপোর্টে যেমন লেখা)">
        <Field label="Surname / পদবি *" name="surname" defaultValue={v("surname")} required maxLength={80} />
        <Field label="Given name / নাম *" name="given_name" defaultValue={v("given_name")} required maxLength={120} />
        <Select label="লিঙ্গ *" name="gender" options={GENDER_LABEL} defaultValue={initial?.gender} required />
        <Field label="জন্মতারিখ *" name="date_of_birth" type="date" defaultValue={v("date_of_birth")} required />
        <Field label="জন্মস্থান" name="place_of_birth" defaultValue={v("place_of_birth")} maxLength={120} />
        <Select label="বৈবাহিক অবস্থা" name="marital_status" options={MARITAL_LABEL} defaultValue={initial?.marital_status} />
        <Field label="পিতার নাম" name="father_name" defaultValue={v("father_name")} maxLength={160} />
        <Field label="মাতার নাম" name="mother_name" defaultValue={v("mother_name")} maxLength={160} />
        <Field label="স্বামী/স্ত্রীর নাম" name="spouse_name" defaultValue={v("spouse_name")} maxLength={160} />
      </Group>
      <Group title="পাসপোর্ট ও পরিচয়পত্র">
        <Field
          label="পাসপোর্ট নম্বর *"
          name="passport_number"
          defaultValue={v("passport_number")}
          required
          maxLength={20}
          autoComplete="off"
          hint="এনক্রিপ্ট করে সংরক্ষিত হয়"
        />
        <Field label="ইস্যুর স্থান" name="passport_issue_place" defaultValue={v("passport_issue_place")} maxLength={120} />
        <Field label="ইস্যুর তারিখ" name="passport_issue_date" type="date" defaultValue={v("passport_issue_date")} />
        <Field label="মেয়াদ শেষ *" name="passport_expiry_date" type="date" defaultValue={v("passport_expiry_date")} required />
        <Field
          label="জাতীয় পরিচয়পত্র (NID)"
          name="nid_number"
          defaultValue={v("nid_number")}
          inputMode="numeric"
          maxLength={25}
          autoComplete="off"
          hint="১০, ১৩ বা ১৭ সংখ্যা"
        />
      </Group>
      <Group title="যোগাযোগ ও অন্যান্য">
        <Field label="মোবাইল" name="phone" type="tel" defaultValue={v("phone")} placeholder="01XXXXXXXXX" maxLength={20} />
        <Field label="ইমেইল" name="email" type="email" defaultValue={v("email")} maxLength={254} />
        <Field label="বর্তমান ঠিকানা" name="present_address" defaultValue={v("present_address")} maxLength={400} />
        <Field label="স্থায়ী ঠিকানা" name="permanent_address" defaultValue={v("permanent_address")} maxLength={400} />
        <Field label="পেশা" name="occupation" defaultValue={v("occupation")} maxLength={120} />
        <Select label="ভিসার ধরন *" name="visa_type" options={VISA_LABEL} defaultValue={initial?.visa_type} required />
        <label className="mb-4 block sm:col-span-2">
          <span className="mb-1 block text-sm font-medium">নোট</span>
          <textarea
            name="notes"
            defaultValue={v("notes")}
            maxLength={4000}
            rows={3}
            className="w-full rounded-lg border border-line bg-bg px-3 py-2 outline-none focus:border-accent"
          />
        </label>
      </Group>
      <Button type="submit" disabled={busy}>
        {busy ? "সংরক্ষণ হচ্ছে…" : createPath ? "আবেদনকারী যোগ করুন" : "পরিবর্তন সংরক্ষণ করুন"}
      </Button>
    </form>
  );
}
