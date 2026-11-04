import type { Metadata } from "next";
import { Suspense } from "react";
import { PageShell } from "@/components/page-shell";
import { AdminAgencies } from "./admin-agencies";

export const metadata: Metadata = { title: "এজেন্সি অনুমোদন" };

export default function AdminAgenciesPage() {
  return (
    <PageShell title="এজেন্সি অনুমোদন (Super admin)">
      <Suspense>
        <AdminAgencies />
      </Suspense>
    </PageShell>
  );
}
