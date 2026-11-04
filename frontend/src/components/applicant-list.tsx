"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Card } from "@/components/page-shell";
import { Notice } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { type ApplicantSummary, daysLeft, VISA_LABEL } from "@/lib/applicants";
import { formatDate } from "@/lib/orgs";

/** Searchable applicant table. `listPath` is the API list endpoint. */
export function ApplicantList({ listPath, newHref, loginNext }: { listPath: string; newHref: string; loginNext: string }) {
  const router = useRouter();
  const [rows, setRows] = useState<ApplicantSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");

  useEffect(() => {
    let alive = true;
    const url = query ? `${listPath}?q=${encodeURIComponent(query)}` : listPath;
    api<ApplicantSummary[]>(url)
      .then((r) => alive && setRows(r))
      .catch((err) => {
        if (!alive) return;
        if (err instanceof ApiError && err.status === 401) router.replace(`/login?next=${loginNext}`);
        else setError(err instanceof ApiError ? err.message : "লোড করা যায়নি।");
      });
    return () => {
      alive = false;
    };
  }, [listPath, query, router, loginNext]);

  return (
    <>
      <div className="mb-4 flex flex-wrap gap-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setQuery(q.trim());
          }}
          className="flex min-w-0 flex-1 gap-2"
        >
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="নাম বা পূর্ণ পাসপোর্ট নম্বর দিয়ে খুঁজুন"
            className="min-w-0 flex-1 rounded-lg border border-line bg-bg-elevated px-3 py-2 outline-none focus:border-accent"
            aria-label="আবেদনকারী খুঁজুন"
          />
          <button className="rounded-lg border border-line px-4 hover:border-accent">খুঁজুন</button>
        </form>
        <Link href={newHref} className="rounded-lg bg-accent px-4 py-2 font-medium text-white dark:text-black">
          + নতুন আবেদনকারী
        </Link>
      </div>
      {error && <Notice tone="error">{error}</Notice>}
      {rows === null && !error && <Notice>লোড হচ্ছে…</Notice>}
      {rows?.length === 0 && <Notice>{query ? "কিছু পাওয়া যায়নি।" : "এখনো কোনো আবেদনকারী যোগ করা হয়নি।"}</Notice>}
      {rows && rows.length > 0 && (
        <Card className="p-0 sm:p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-line text-muted">
                <tr>
                  <th className="px-4 py-3 font-normal">নাম</th>
                  <th className="px-4 py-3 font-normal">পাসপোর্ট</th>
                  <th className="px-4 py-3 font-normal">মেয়াদ</th>
                  <th className="px-4 py-3 font-normal">ভিসা</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {rows.map((a) => {
                  const left = daysLeft(a.passport_expiry_date);
                  return (
                    <tr key={a.id} className="hover:bg-bg-sunken">
                      <td className="px-4 py-3">
                        <Link href={`/applicants/${a.id}`} className="font-medium text-accent">
                          {a.given_name} {a.surname}
                        </Link>
                        <div className="text-xs text-muted">জন্ম {formatDate(a.date_of_birth)}</div>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs">{a.passport_masked}</td>
                      <td className={`px-4 py-3 ${left < 183 ? "text-amber-600" : ""}`}>
                        {formatDate(a.passport_expiry_date)}
                      </td>
                      <td className="px-4 py-3">{VISA_LABEL[a.visa_type]}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </>
  );
}
