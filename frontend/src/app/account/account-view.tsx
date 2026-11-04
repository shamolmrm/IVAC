"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Button, Field, Notice } from "@/components/ui";
import { api, ApiError, post, type User, useSession } from "@/lib/api";

export function AccountView() {
  const { user, loading, setUser } = useSession();
  const router = useRouter();
  const welcome = useSearchParams().get("welcome") === "1";

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) return <Notice>লোড হচ্ছে…</Notice>;

  async function logout() {
    await post("/auth/logout").catch(() => undefined);
    router.replace("/login");
  }

  return (
    <>
      <div className="mb-6 flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">আমার অ্যাকাউন্ট</h1>
        <button onClick={logout} className="rounded-lg border border-line px-3 py-1.5 text-sm hover:border-accent">
          লগআউট
        </button>
      </div>
      {welcome && <Notice tone="success">স্বাগতম, {user.full_name}! আপনার অ্যাকাউন্ট খোলা হয়েছে।</Notice>}

      <section className="mb-6 rounded-2xl border border-line bg-bg-elevated p-6">
        <dl className="grid gap-3 text-sm sm:grid-cols-[10rem_1fr]">
          <dt className="text-muted">নাম</dt>
          <dd>{user.full_name}</dd>
          <dt className="text-muted">ইমেইল</dt>
          <dd className="break-all">
            {user.email}{" "}
            <span className={user.email_verified ? "text-emerald-600" : "text-amber-600"}>
              {user.email_verified ? "✓ যাচাইকৃত" : "• যাচাই বাকি"}
            </span>
          </dd>
          <dt className="text-muted">মোবাইল</dt>
          <dd>
            {user.phone_verified && user.phone ? (
              <>
                {user.phone} <span className="text-emerald-600">✓ যাচাইকৃত</span>
              </>
            ) : (
              <span className="text-amber-600">• যোগ করা হয়নি</span>
            )}
          </dd>
        </dl>
        {!user.email_verified && <VerifyPrompt />}
      </section>

      {!user.phone_verified && <PhoneSection onVerified={setUser} />}

      <ChangePassword />

      <p className="mt-8 flex flex-wrap justify-center gap-4 text-sm">
        <Link href="/applicants" className="text-accent">
          আমার আবেদনকারী
        </Link>
        <Link href="/agency" className="text-accent">
          এজেন্সি
        </Link>
        {user.is_superadmin && (
          <Link href="/admin/agencies" className="text-accent">
            এজেন্সি অনুমোদন (admin)
          </Link>
        )}
        <Link href="/" className="text-accent">
          হোম
        </Link>
      </p>
    </>
  );
}

function VerifyPrompt() {
  const [emailOn, setEmailOn] = useState<boolean | null>(null);
  const [msg, setMsg] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<{ email: boolean }>("/auth/features")
      .then((f) => setEmailOn(f.email))
      .catch(() => setEmailOn(false));
  }, []);

  async function resend() {
    setBusy(true);
    try {
      await post("/auth/verify/request");
      setMsg({ tone: "success", text: "যাচাইয়ের লিংক আপনার ইমেইলে পাঠানো হয়েছে।" });
    } catch (err) {
      setMsg({ tone: "error", text: err instanceof ApiError ? err.message : "পাঠানো যায়নি।" });
    } finally {
      setBusy(false);
    }
  }

  if (emailOn === null) return null;
  return (
    <div className="mt-5 border-t border-line pt-4 text-sm">
      {msg && <Notice tone={msg.tone}>{msg.text}</Notice>}
      {emailOn ? (
        <button onClick={resend} disabled={busy} className="font-medium text-accent disabled:opacity-60">
          {busy ? "পাঠানো হচ্ছে…" : "যাচাইয়ের লিংক আবার পাঠান"}
        </button>
      ) : (
        <p className="text-muted">ইমেইল যাচাই সেবা শীঘ্রই চালু হবে।</p>
      )}
    </div>
  );
}

function PhoneSection({ onVerified }: { onVerified: (u: User) => void }) {
  const [smsOn, setSmsOn] = useState<boolean | null>(null);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<{ sms: boolean }>("/auth/features")
      .then((f) => setSmsOn(f.sms))
      .catch(() => setSmsOn(false));
  }, []);

  async function requestCode(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const phone = String(new FormData(e.currentTarget).get("phone")).trim();
    setBusy(true);
    setMsg(null);
    try {
      const r = await post<{ status: string; phone?: string }>("/auth/phone/request", { phone });
      setSentTo(r.phone ?? phone);
      setMsg({ tone: "success", text: "৬ সংখ্যার কোড SMS-এ পাঠানো হয়েছে। ৫ মিনিট বৈধ।" });
    } catch (err) {
      setMsg({ tone: "error", text: err instanceof ApiError ? err.message : "কোড পাঠানো যায়নি।" });
    } finally {
      setBusy(false);
    }
  }

  async function verifyCode(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const code = String(new FormData(e.currentTarget).get("code")).trim();
    setBusy(true);
    setMsg(null);
    try {
      onVerified(await post<User>("/auth/phone/verify", { code }));
    } catch (err) {
      setMsg({ tone: "error", text: err instanceof ApiError ? err.message : "যাচাই করা যায়নি।" });
      setBusy(false);
    }
  }

  if (smsOn === null) return null;
  return (
    <section className="mb-6 rounded-2xl border border-line bg-bg-elevated p-6">
      <h2 className="mb-4 font-semibold">মোবাইল নম্বর যাচাই</h2>
      {msg && <Notice tone={msg.tone}>{msg.text}</Notice>}
      {!smsOn ? (
        <p className="text-sm text-muted">SMS যাচাই সেবা শীঘ্রই চালু হবে।</p>
      ) : sentTo ? (
        <form onSubmit={verifyCode}>
          <Field
            label={`${sentTo} নম্বরে পাঠানো কোড`}
            name="code"
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="\d{6}"
            maxLength={6}
            required
          />
          <Button type="submit" disabled={busy}>
            {busy ? "যাচাই হচ্ছে…" : "যাচাই করুন"}
          </Button>
          <button type="button" onClick={() => setSentTo(null)} className="mt-3 w-full text-sm text-accent">
            অন্য নম্বর দিন / আবার কোড চান
          </button>
        </form>
      ) : (
        <form onSubmit={requestCode}>
          <Field
            label="মোবাইল নম্বর"
            name="phone"
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            placeholder="01XXXXXXXXX"
            required
          />
          <Button type="submit" disabled={busy}>
            {busy ? "পাঠানো হচ্ছে…" : "কোড পাঠান"}
          </Button>
        </form>
      )}
    </section>
  );
}

function ChangePassword() {
  const [msg, setMsg] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    const next = String(form.get("new_password"));
    if (next !== String(form.get("confirm"))) {
      setMsg({ tone: "error", text: "দুটো নতুন পাসওয়ার্ড একই হয়নি।" });
      return;
    }
    setBusy(true);
    try {
      await post("/auth/password/change", {
        current_password: String(form.get("current_password")),
        new_password: next,
      });
      formEl.reset();
      setMsg({ tone: "success", text: "পাসওয়ার্ড বদলানো হয়েছে। অন্য সব ডিভাইস থেকে লগআউট করা হয়েছে।" });
    } catch (err) {
      setMsg({ tone: "error", text: err instanceof ApiError ? err.message : "বদলানো যায়নি।" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-2xl border border-line bg-bg-elevated p-6">
      <h2 className="mb-4 font-semibold">পাসওয়ার্ড বদলান</h2>
      <form onSubmit={onSubmit}>
        {msg && <Notice tone={msg.tone}>{msg.text}</Notice>}
        <Field label="বর্তমান পাসওয়ার্ড" name="current_password" type="password" autoComplete="current-password" required />
        <Field
          label="নতুন পাসওয়ার্ড"
          name="new_password"
          type="password"
          autoComplete="new-password"
          required
          minLength={10}
          hint="কমপক্ষে ১০ অক্ষর।"
        />
        <Field label="নতুন পাসওয়ার্ড আবার" name="confirm" type="password" autoComplete="new-password" required />
        <Button type="submit" disabled={busy}>
          {busy ? "অপেক্ষা করুন…" : "পাসওয়ার্ড বদলান"}
        </Button>
      </form>
    </section>
  );
}
