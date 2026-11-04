"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/page-shell";
import { Notice } from "@/components/ui";
import { api, ApiError, post } from "@/lib/api";
import { type AdminOrg, formatDate, type OrgStatus, STATUS_LABEL } from "@/lib/orgs";

const FILTERS: Array<{ value: OrgStatus | ""; label: string }> = [
  { value: "pending", label: "অপেক্ষমাণ" },
  { value: "active", label: "সক্রিয়" },
  { value: "suspended", label: "স্থগিত" },
  { value: "", label: "সব" },
];

export function AdminAgencies() {
  const [filter, setFilter] = useState<OrgStatus | "">("pending");
  const [orgs, setOrgs] = useState<AdminOrg[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let alive = true;
    api<AdminOrg[]>(`/admin/orgs${filter ? `?status=${filter}` : ""}`)
      .then((o) => alive && setOrgs(o))
      .catch((err) => alive && setError(err instanceof ApiError ? err.message : "লোড করা যায়নি।"));
    return () => {
      alive = false;
    };
  }, [filter, reload]);

  async function setStatus(id: string, status: OrgStatus) {
    try {
      await post(`/admin/orgs/${id}/status`, { status });
      setReload((n) => n + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "পরিবর্তন করা যায়নি।");
    }
  }

  return (
    <>
      <div className="mb-4 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.value || "all"}
            onClick={() => setFilter(f.value)}
            className={`rounded-full border px-3 py-1 text-sm ${filter === f.value ? "border-accent text-accent" : "border-line"}`}
          >
            {f.label}
          </button>
        ))}
      </div>
      {error && <Notice tone="error">{error}</Notice>}
      {orgs === null && !error && <Notice>লোড হচ্ছে…</Notice>}
      {orgs?.length === 0 && <Notice>কোনো এজেন্সি নেই।</Notice>}
      {orgs?.map((o) => (
        <Card key={o.id}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="font-semibold">{o.name}</h2>
              <p className="text-sm text-muted">
                {o.owner_email ?? "—"} · {o.phone || "ফোন নেই"} · সদস্য {o.members} · {formatDate(o.created_at)}
              </p>
              <p className="text-sm text-muted">
                ট্রেড লাইসেন্স: {o.trade_license || "—"} · ঠিকানা: {o.address || "—"}
              </p>
            </div>
            <span className={`text-sm ${STATUS_LABEL[o.status].cls}`}>{STATUS_LABEL[o.status].text}</span>
          </div>
          <div className="mt-4 flex gap-2">
            {o.status !== "active" && (
              <button
                onClick={() => setStatus(o.id, "active")}
                className="rounded-lg bg-accent px-3 py-1.5 text-sm text-white dark:text-black"
              >
                অনুমোদন দিন
              </button>
            )}
            {o.status !== "suspended" && (
              <button
                onClick={() => setStatus(o.id, "suspended")}
                className="rounded-lg border border-red-300 px-3 py-1.5 text-sm text-red-600"
              >
                স্থগিত করুন
              </button>
            )}
          </div>
        </Card>
      ))}
    </>
  );
}
