import type { Metadata } from "next";
import { Suspense } from "react";
import { PageShell } from "@/components/page-shell";
import { Notice } from "@/components/ui";
import { AgencyApplicants } from "./agency-applicants";

export const metadata: Metadata = { title: "এজেন্সির আবেদনকারী" };

export default function AgencyApplicantsPage() {
  return (
    <PageShell title="এজেন্সির আবেদনকারী">
      <Suspense fallback={<Notice>লোড হচ্ছে…</Notice>}>
        <AgencyApplicants />
      </Suspense>
    </PageShell>
  );
}
