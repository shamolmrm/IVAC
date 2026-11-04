"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Button, Notice } from "@/components/ui";
import { ApiError, post, useSession } from "@/lib/api";
import { type Org, type OrgRole, ROLE_LABEL } from "@/lib/orgs";

type Preview = { organization: string; role: OrgRole; email: string };

export function AcceptInvite() {
  const token = useSearchParams().get("token") ?? "";
  const router = useRouter();
  const { user, loading } = useSession();
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState<string | null>(token ? null : "লিংকটি সঠিক নয়।");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!user || !token) return;
    let alive = true;
    post<Preview>("/invites/preview", { token })
      .then((p) => alive && setPreview(p))
      .catch((err) => alive && setError(err instanceof ApiError ? err.message : "আমন্ত্রণ পড়া যায়নি।"));
    return () => {
      alive = false;
    };
  }, [user, token]);

  async function accept() {
    setBusy(true);
    try {
      const org = await post<Org>("/invites/accept", { token });
      router.push(`/agency/${org.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "যোগ দেওয়া যায়নি।");
      setBusy(false);
    }
  }

  if (error) return <Notice tone="error">{error}</Notice>;
  if (loading) return <Notice>লোড হচ্ছে…</Notice>;

  const next = encodeURIComponent(`/invite?token=${token}`);
  if (!user)
    return (
      <>
        <p className="mb-4 text-sm text-muted">
          আমন্ত্রণ গ্রহণ করতে যে ইমেইলে আমন্ত্রণ এসেছে সেই ইমেইলের অ্যাকাউন্ট দিয়ে লগইন করুন। অ্যাকাউন্ট না থাকলে নতুন খুলুন।
        </p>
        <div className="flex gap-3">
          <Link href={`/login?next=${next}`} className="rounded-lg bg-accent px-4 py-2 font-medium text-white dark:text-black">
            লগইন
          </Link>
          <Link href={`/register?next=${next}`} className="rounded-lg border border-line px-4 py-2 font-medium">
            অ্যাকাউন্ট খুলুন
          </Link>
        </div>
      </>
    );

  if (!preview) return <Notice>লোড হচ্ছে…</Notice>;
  return (
    <>
      <p className="mb-4">
        <strong>{preview.organization}</strong> এজেন্সিতে <strong>{ROLE_LABEL[preview.role]}</strong> হিসেবে যোগ দেওয়ার
        আমন্ত্রণ।
      </p>
      {preview.email !== user.email && (
        <Notice tone="error">
          আমন্ত্রণটি {preview.email} ঠিকানার জন্য, কিন্তু আপনি {user.email} দিয়ে লগইন করা আছেন।
        </Notice>
      )}
      <Button onClick={accept} disabled={busy || preview.email !== user.email}>
        {busy ? "অপেক্ষা করুন…" : "আমন্ত্রণ গ্রহণ করুন"}
      </Button>
    </>
  );
}
