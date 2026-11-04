import type { Metadata } from "next";
import { Suspense } from "react";
import { PageShell } from "@/components/page-shell";
import { NewApplicant } from "./new-applicant";

export const metadata: Metadata = { title: "নতুন আবেদনকারী" };

export default function NewApplicantPage() {
  return (
    <PageShell title="নতুন আবেদনকারী">
      <Suspense>
        <NewApplicant />
      </Suspense>
    </PageShell>
  );
}
