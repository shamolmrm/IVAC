"use client";

import Link from "next/link";
import { useState } from "react";
import { AuthShell, Button, Field, Notice } from "@/components/ui";
import { ApiError, post } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const email = String(new FormData(e.currentTarget).get("email")).trim();
    setBusy(true);
    setError(null);
    try {
      const r = await post<{ status: string }>("/auth/password/forgot", { email });
      setMessage(r.status);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "কিছু একটা সমস্যা হয়েছে।");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title="পাসওয়ার্ড রিসেট"
      footer={
        <Link href="/login" className="font-medium text-accent">
          লগইনে ফিরে যান
        </Link>
      }
    >
      {message ? (
        <Notice tone="success">{message}</Notice>
      ) : (
        <form onSubmit={onSubmit}>
          {error && <Notice tone="error">{error}</Notice>}
          <p className="mb-4 text-sm text-muted">আপনার ইমেইল দিন। পাসওয়ার্ড রিসেটের লিংক পাঠানো হবে।</p>
          <Field label="ইমেইল" name="email" type="email" autoComplete="email" required />
          <Button type="submit" disabled={busy}>
            {busy ? "অপেক্ষা করুন…" : "রিসেট লিংক পাঠান"}
          </Button>
        </form>
      )}
    </AuthShell>
  );
}
