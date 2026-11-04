"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Notice } from "@/components/ui";
import { ApiError, post } from "@/lib/api";

export function Verify() {
  const token = useSearchParams().get("token") ?? "";
  const [state, setState] = useState<"working" | "done" | string>(token ? "working" : "লিংকটি সঠিক নয়।");
  const sent = useRef(false);

  useEffect(() => {
    if (!token || sent.current) return;
    sent.current = true; // tokens are single use: never confirm twice
    post("/auth/verify/confirm", { token })
      .then(() => setState("done"))
      .catch((err) => setState(err instanceof ApiError ? err.message : "যাচাই করা যায়নি।"));
  }, [token]);

  if (state === "working") return <Notice>যাচাই করা হচ্ছে…</Notice>;
  return (
    <>
      {state === "done" ? (
        <Notice tone="success">আপনার ইমেইল সফলভাবে যাচাই হয়েছে।</Notice>
      ) : (
        <Notice tone="error">{state}</Notice>
      )}
      <Link href="/account" className="font-medium text-accent">
        অ্যাকাউন্টে যান →
      </Link>
    </>
  );
}
