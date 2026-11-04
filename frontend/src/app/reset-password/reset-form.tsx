"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Button, Field, Notice } from "@/components/ui";
import { ApiError, post } from "@/lib/api";

export function ResetForm() {
  const token = useSearchParams().get("token") ?? "";
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!token) return <Notice tone="error">লিংকটি সঠিক নয়। ইমেইলের পুরো লিংকটি খুলুন।</Notice>;

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
      await post("/auth/password/reset", { token, password });
      router.push("/account");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "কিছু একটা সমস্যা হয়েছে।");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit}>
      {error && <Notice tone="error">{error}</Notice>}
      <Field
        label="নতুন পাসওয়ার্ড"
        name="password"
        type="password"
        autoComplete="new-password"
        required
        minLength={10}
        hint="কমপক্ষে ১০ অক্ষর।"
      />
      <Field label="আবার লিখুন" name="confirm" type="password" autoComplete="new-password" required />
      <Button type="submit" disabled={busy}>
        {busy ? "অপেক্ষা করুন…" : "পাসওয়ার্ড সংরক্ষণ করুন"}
      </Button>
    </form>
  );
}
