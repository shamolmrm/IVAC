import type { Metadata } from "next";
import { Suspense } from "react";
import { PageShell } from "@/components/page-shell";
import { AgencyList } from "./agency-list";

export const metadata: Metadata = { title: "এজেন্সি" };

export default function AgencyPage() {
  return (
    <PageShell title="আমার এজেন্সি">
      <Suspense>
        <AgencyList />
      </Suspense>
    </PageShell>
  );
}
