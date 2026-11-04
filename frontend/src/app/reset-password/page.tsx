import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthShell } from "@/components/ui";
import { ResetForm } from "./reset-form";

export const metadata: Metadata = { title: "নতুন পাসওয়ার্ড" };

export default function ResetPasswordPage() {
  return (
    <AuthShell title="নতুন পাসওয়ার্ড দিন">
      <Suspense>
        <ResetForm />
      </Suspense>
    </AuthShell>
  );
}
