"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ApplicantForm } from "@/components/applicant-form";

export function NewApplicant() {
  const router = useRouter();
  const org = useSearchParams().get("org");
  const valid = !org || /^[0-9a-f-]{36}$/i.test(org);
  const back = org && valid ? `/agency/${org}/applicants` : "/applicants";

  if (!valid) return <p className="text-sm text-red-600">লিংকটি সঠিক নয়।</p>;
  return (
    <>
      <Link href={back} className="mb-4 inline-block text-sm text-accent">
        ← তালিকায় ফিরুন
      </Link>
      <ApplicantForm
        createPath={org ? `/orgs/${org}/applicants` : "/applicants"}
        onSaved={(s) => {
          const w = s.warnings.length ? `?w=${encodeURIComponent(s.warnings.join("\n"))}` : "";
          router.push(`/applicants/${s.applicant.id}${w}`);
        }}
      />
    </>
  );
}
