"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button, Field, Notice } from "@/components/ui";
import { ApiError, post, type User } from "@/lib/api";

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setBusy(true);
    setError(null);
    try {
      await post<User>("/auth/login", {
        email: String(form.get("email")).trim(),
        password: String(form.get("password")),
      });
      router.push("/account");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "কিছু একটা সমস্যা হয়েছে।");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit}>
      {error && <Notice tone="error">{error}</Notice>}
      <Field label="ইমেইল" name="email" type="email" autoComplete="email" required />
      <Field label="পাসওয়ার্ড" name="password" type="password" autoComplete="current-password" required />
      <div className="-mt-2 mb-4 text-right text-sm">
        <Link href="/forgot-password" className="text-accent">
          পাসওয়ার্ড ভুলে গেছেন?
        </Link>
      </div>
      <Button type="submit" disabled={busy}>
        {busy ? "অপেক্ষা করুন…" : "লগইন"}
      </Button>
    </form>
  );
}
