"use client";

import { useCallback, useEffect, useState } from "react";
import { Card } from "@/components/page-shell";
import { Notice } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { formatDate } from "@/lib/orgs";

export type DocKind =
  | "passport_bio"
  | "photo"
  | "bgd_form"
  | "nid"
  | "bank_statement"
  | "address_proof"
  | "previous_visa"
  | "medical_letter"
  | "invitation_letter"
  | "student_letter"
  | "other";

export const DOC_LABEL: Record<DocKind, string> = {
  passport_bio: "পাসপোর্টের তথ্য পাতা",
  photo: "ছবি",
  bgd_form: "অনলাইন আবেদন ফর্ম (BGD)",
  nid: "জাতীয় পরিচয়পত্র",
  bank_statement: "ব্যাংক স্টেটমেন্ট",
  address_proof: "ঠিকানার প্রমাণ",
  previous_visa: "আগের ভিসা",
  medical_letter: "চিকিৎসার কাগজ / হাসপাতালের চিঠি",
  invitation_letter: "আমন্ত্রণপত্র",
  student_letter: "ভর্তির কাগজ",
  other: "অন্যান্য",
};

type Doc = { id: string; kind: DocKind; original_name: string; content_type: string; size: number; created_at: string | null };
type Data = { documents: Doc[]; checklist: Array<{ kind: DocKind; done: boolean }>; complete: boolean };

const kb = (n: number) => (n < 1024 * 1024 ? `${Math.ceil(n / 1024)} KB` : `${(n / 1024 / 1024).toFixed(1)} MB`);

export function DocumentsPanel({ applicantId }: { applicantId: string }) {
  const [data, setData] = useState<Data | null>(null);
  const [msg, setMsg] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [kind, setKind] = useState<DocKind>("passport_bio");

  const load = useCallback(() => api<Data>(`/applicants/${applicantId}/documents`), [applicantId]);

  useEffect(() => {
    let alive = true;
    load()
      .then((d) => {
        if (!alive) return;
        setData(d);
        const missing = d.checklist.find((i) => !i.done);
        if (missing) setKind(missing.kind);
      })
      .catch((err) => alive && setMsg({ tone: "error", text: err instanceof ApiError ? err.message : "লোড করা যায়নি।" }));
    return () => {
      alive = false;
    };
  }, [load]);

  async function onUpload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const file = (formEl.elements.namedItem("file") as HTMLInputElement).files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      setMsg({ tone: "error", text: "ফাইল ১০ MB-এর বেশি হতে পারবে না।" });
      return;
    }
    const body = new FormData();
    body.append("kind", kind);
    body.append("file", file);
    setBusy(true);
    setMsg(null);
    try {
      const r = await fetch(`/api/v1/applicants/${applicantId}/documents`, { method: "POST", body, credentials: "include" });
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        throw new ApiError(r.status, typeof j.detail === "string" ? j.detail : "আপলোড করা যায়নি।");
      }
      formEl.reset();
      const d = await load();
      setData(d);
      const missing = d.checklist.find((i) => !i.done);
      if (missing) setKind(missing.kind);
      setMsg({ tone: "success", text: `${DOC_LABEL[kind]} আপলোড হয়েছে।` });
    } catch (err) {
      setMsg({ tone: "error", text: err instanceof ApiError ? err.message : "আপলোড করা যায়নি।" });
    } finally {
      setBusy(false);
    }
  }

  async function remove(doc: Doc) {
    if (!window.confirm(`"${doc.original_name}" মুছে ফেলবেন?`)) return;
    try {
      await api(`/documents/${doc.id}`, { method: "DELETE" });
      setData(await load());
    } catch (err) {
      setMsg({ tone: "error", text: err instanceof ApiError ? err.message : "মোছা যায়নি।" });
    }
  }

  return (
    <Card>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold">ডকুমেন্ট</h2>
        {data && (
          <span className={`text-sm ${data.complete ? "text-emerald-600" : "text-amber-600"}`}>
            {data.complete
              ? "✓ প্রয়োজনীয় সব কাগজ আছে"
              : `${data.checklist.filter((i) => !i.done).length}টি কাগজ বাকি`}
          </span>
        )}
      </div>
      {msg && <Notice tone={msg.tone}>{msg.text}</Notice>}

      {data && (
        <ul className="mb-5 grid gap-2 sm:grid-cols-2">
          {data.checklist.map((i) => (
            <li
              key={i.kind}
              className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm ${
                i.done ? "border-emerald-300 dark:border-emerald-900" : "border-line"
              }`}
            >
              <span className={i.done ? "text-emerald-600" : "text-muted"}>{i.done ? "✓" : "○"}</span>
              {DOC_LABEL[i.kind]}
            </li>
          ))}
        </ul>
      )}
      <p className="mb-4 text-xs text-muted">
        এটি সাধারণ চেকলিস্ট। ভিসার ধরন ও IVAC-এর সর্বশেষ নির্দেশনা অনুযায়ী আরও কাগজ লাগতে পারে।
      </p>

      <form onSubmit={onUpload} className="mb-6 grid gap-3 rounded-xl bg-bg-sunken p-4 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
        <label className="block text-sm">
          <span className="mb-1 block font-medium">কাগজের ধরন</span>
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value as DocKind)}
            className="w-full rounded-lg border border-line bg-bg-elevated px-3 py-2"
          >
            {(Object.keys(DOC_LABEL) as DocKind[]).map((k) => (
              <option key={k} value={k}>
                {DOC_LABEL[k]}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-medium">ফাইল (JPG, PNG, PDF · সর্বোচ্চ ১০ MB)</span>
          <input
            name="file"
            type="file"
            required
            accept="image/jpeg,image/png,application/pdf"
            className="w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-accent file:px-3 file:py-2 file:text-white dark:file:text-black"
          />
        </label>
        <button
          disabled={busy}
          className="rounded-lg bg-accent px-4 py-2 font-medium text-white disabled:opacity-60 dark:text-black"
        >
          {busy ? "আপলোড হচ্ছে…" : "আপলোড"}
        </button>
      </form>

      {data && data.documents.length > 0 && (
        <ul className="divide-y divide-line text-sm">
          {data.documents.map((d) => (
            <li key={d.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <div className="min-w-0">
                <div className="font-medium">{DOC_LABEL[d.kind]}</div>
                <div className="truncate text-xs text-muted">
                  {d.original_name} · {kb(d.size)} · {formatDate(d.created_at)}
                </div>
              </div>
              <div className="flex gap-3 text-xs">
                <a href={`/api/v1/documents/${d.id}/download?inline=true`} target="_blank" rel="noopener" className="text-accent">
                  দেখুন
                </a>
                <a href={`/api/v1/documents/${d.id}/download`} className="text-accent">
                  ডাউনলোড
                </a>
                <button onClick={() => remove(d)} className="text-red-600">
                  মুছুন
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
