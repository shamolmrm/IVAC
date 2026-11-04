"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ApplicantList } from "@/components/applicant-list";

export function AgencyApplicants() {
  const { id } = useParams<{ id: string }>();
  return (
    <>
      <Link href={`/agency/${id}`} className="mb-4 inline-block text-sm text-accent">
        ← এজেন্সিতে ফিরুন
      </Link>
      <ApplicantList
        listPath={`/orgs/${id}/applicants`}
        newHref={`/applicants/new?org=${id}`}
        loginNext={`/agency/${id}/applicants`}
      />
    </>
  );
}
