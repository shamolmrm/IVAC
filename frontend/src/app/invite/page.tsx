import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthShell } from "@/components/ui";
import { AcceptInvite } from "./accept-invite";

export const metadata: Metadata = { title: "এজেন্সিতে আমন্ত্রণ" };

export default function InvitePage() {
  return (
    <AuthShell title="এজেন্সিতে আমন্ত্রণ">
      <Suspense>
        <AcceptInvite />
      </Suspense>
    </AuthShell>
  );
}
