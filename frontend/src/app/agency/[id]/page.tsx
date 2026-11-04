import type { Metadata } from "next";
import { Suspense } from "react";
import { Notice } from "@/components/ui";
import { AgencyDetail } from "./agency-detail";

export const metadata: Metadata = { title: "এজেন্সি" };

export default function AgencyDetailPage() {
  return (
    <Suspense fallback={<Notice>লোড হচ্ছে…</Notice>}>
      <AgencyDetail />
    </Suspense>
  );
}
