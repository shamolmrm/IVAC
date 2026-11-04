import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { AuthShell } from "@/components/ui";
import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "লগইন" };

export default function LoginPage() {
  return (
    <AuthShell
      title="লগইন করুন"
      footer={
        <>
          অ্যাকাউন্ট নেই?{" "}
          <Link href="/register" className="font-medium text-accent">
            নতুন অ্যাকাউন্ট খুলুন
          </Link>
        </>
      }
    >
      <Suspense>
        <LoginForm />
      </Suspense>
    </AuthShell>
  );
}
