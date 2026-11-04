import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthShell } from "@/components/ui";
import { Verify } from "./verify";

export const metadata: Metadata = { title: "ইমেইল যাচাই" };

export default function VerifyEmailPage() {
  return (
    <AuthShell title="ইমেইল যাচাই">
      <Suspense>
        <Verify />
      </Suspense>
    </AuthShell>
  );
}
