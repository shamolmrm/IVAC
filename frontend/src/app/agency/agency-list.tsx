"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Card } from "@/components/page-shell";
import { Button, Field, Notice } from "@/components/ui";
import { api, ApiError, post } from "@/lib/api";
import { type Org, ROLE_LABEL, STATUS_LABEL } from "@/lib/orgs";

export function AgencyList() {
  const router = useRouter();
  const [orgs, setOrgs] = useState<Org[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Org[]>("/orgs/mine")
      .then(setOrgs)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) router.replace("/login?next=/agency");
        else setError(err instanceof ApiError ? err.message : "লোড করা যায়নি।");
      });
  }, [router]);

  async function create(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const value = (k: string) => String(form.get(k) ?? "").trim() || null;
    setBusy(true);
    setError(null);
    try {
      const org = await post<Org>("/orgs", {
        name: value("name"),
        phone: value("phone"),
        address: value("address"),
        trade_license: value("trade_license"),
      });
      router.push(`/agency/${org.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "এজেন্সি খোলা যায়নি।");
      setBusy(false);
    }
  }

  if (orgs === null && !error) return <Notice>লোড হচ্ছে…</Notice>;

  return (
    <>
      {error && <Notice tone="error">{error}</Notice>}
      {orgs && orgs.length > 0 && (
        <Card>
          <ul className="divide-y divide-line">
            {orgs.map((o) => (
              <li key={o.id}>
                <Link href={`/agency/${o.id}`} className="flex flex-wrap items-center justify-between gap-2 py-3 hover:text-accent">
                  <span className="font-medium">{o.name}</span>
                  <span className="text-sm text-muted">
                    {o.my_role && ROLE_LABEL[o.my_role]} ·{" "}
                    <span className={STATUS_LABEL[o.status].cls}>{STATUS_LABEL[o.status].text}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}
      <Card>
        <h2 className="mb-1 font-semibold">নতুন এজেন্সি খুলুন</h2>
        <p className="mb-4 text-sm text-muted">
          আপনি এজেন্সির Owner হবেন। অনুমোদনের পর staff যোগ করতে ও আবেদনকারী ব্যবস্থাপনা করতে পারবেন।
        </p>
        <form onSubmit={create}>
          <Field label="এজেন্সির নাম" name="name" required minLength={2} maxLength={160} />
          <Field label="ফোন" name="phone" type="tel" maxLength={20} />
          <Field label="ঠিকানা" name="address" maxLength={300} />
          <Field label="ট্রেড লাইসেন্স নম্বর" name="trade_license" maxLength={60} />
          <Button type="submit" disabled={busy}>
            {busy ? "অপেক্ষা করুন…" : "এজেন্সি খুলুন"}
          </Button>
        </form>
      </Card>
    </>
  );
}
