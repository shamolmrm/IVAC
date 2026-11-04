"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Button, Field, Notice } from "@/components/ui";
import { ApiError, post, type User } from "@/lib/api";
import { safeNext } from "@/lib/orgs";

export function RegisterForm() {
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"), "/account?welcome=1");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const password = String(form.get("password"));
    if (password !== String(form.get("confirm"))) {
      setError("দুটো পাসওয়ার্ড একই হয়নি।");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await post<User>("/auth/register", {
        full_name: String(form.get("full_name")).trim(),
        email: String(form.get("email")).trim(),
        password,
      });
      router.push(next);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "কিছু একটা সমস্যা হয়েছে।");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit}>
      {error && <Notice tone="error">{error}</Notice>}
      <Field label="পূর্ণ নাম" name="full_name" autoComplete="name" required minLength={2} maxLength={120} />
      <Field label="ইমেইল" name="email" type="email" autoComplete="email" required maxLength={254} />
      <Field
        label="পাসওয়ার্ড"
        name="password"
        type="password"
        autoComplete="new-password"
        required
        minLength={10}
        maxLength={200}
        hint="কমপক্ষে ১০ অক্ষর।"
      />
      <Field label="পাসওয়ার্ড আবার লিখুন" name="confirm" type="password" autoComplete="new-password" required />
      <p className="mb-4 text-xs text-muted">
        অ্যাকাউন্ট খুলে আপনি সম্মতি দিচ্ছেন যে ভিসা আবেদনের প্রস্তুতির জন্য আপনার দেওয়া তথ্য নিরাপদে সংরক্ষণ ও প্রক্রিয়া
        করা হবে। এটি IVAC-এর অফিসিয়াল সেবা নয়।
      </p>
      <Button type="submit" disabled={busy}>
        {busy ? "অপেক্ষা করুন…" : "অ্যাকাউন্ট খুলুন"}
      </Button>
    </form>
  );
}
