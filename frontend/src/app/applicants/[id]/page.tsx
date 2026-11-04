import type { Metadata } from "next";
import { Suspense } from "react";
import { Notice } from "@/components/ui";
import { ApplicantDetail } from "./applicant-detail";

export const metadata: Metadata = { title: "আবেদনকারী" };

export default function ApplicantPage() {
  return (
    <Suspense fallback={<Notice>লোড হচ্ছে…</Notice>}>
      <ApplicantDetail />
    </Suspense>
  );
}
