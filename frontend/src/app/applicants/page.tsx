import type { Metadata } from "next";
import { Suspense } from "react";
import { ApplicantList } from "@/components/applicant-list";
import { PageShell } from "@/components/page-shell";

export const metadata: Metadata = { title: "আমার আবেদনকারী" };

export default function MyApplicantsPage() {
  return (
    <PageShell title="আমার আবেদনকারী">
      <p className="-mt-3 mb-6 text-sm text-muted">নিজের ও পরিবারের সদস্যদের ভিসা আবেদনের তথ্য এখানে রাখুন।</p>
      <Suspense>
        <ApplicantList listPath="/applicants" newHref="/applicants/new" loginNext="/applicants" />
      </Suspense>
    </PageShell>
  );
}
