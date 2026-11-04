import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { AuthShell } from "@/components/ui";
import { RegisterForm } from "./register-form";

export const metadata: Metadata = { title: "অ্যাকাউন্ট খুলুন" };

export default function RegisterPage() {
  return (
    <AuthShell
      title="নতুন অ্যাকাউন্ট খুলুন"
      footer={
        <>
          আগেই অ্যাকাউন্ট আছে?{" "}
          <Link href="/login" className="font-medium text-accent">
            লগইন করুন
          </Link>
        </>
      }
    >
      <Suspense>
        <RegisterForm />
      </Suspense>
    </AuthShell>
  );
}
